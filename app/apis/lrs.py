from datetime import datetime, timezone
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Blueprint, json, jsonify, render_template, request

from app.classes.logging import get_route_loggers, _client_ip
from app.db import db
from app.models.activities import Activity
from app.models.agents import Agent
from app.models.statements import Statement


blp = Blueprint('lrs', __name__, url_prefix='/api/lrs')

_loggers = get_route_loggers('lrs')
access_logger = _loggers.access
error_logger = _loggers.error
activity_logger = _loggers.activity

# Authentication decorator for API endpoints
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            access_logger.warning(
                'LRS authentication failed | path=%s | ip=%s',
                request.path,
                _client_ip()
            )
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def check_auth(username, password):
    # Simple authentication - in production, use proper user management
    # return username == 'lrs_user' and password == 'lrs_password'
    return True

@blp.route('/activities/state', methods=['GET'])
def get_activity_state():
    state_id = request.args.get("stateId")
    activity_id = request.args.get("activityId")
    agent = request.args.get("agent")  # This will be a JSON string
    access_logger.info(
        'LRS activity state request | state_id=%s | activity_id=%s | ip=%s',
        state_id,
        activity_id,
        _client_ip()
    )
    
    # Optional: Parse agent JSON safely
    try:
        agent_data = json.loads(agent) if agent else {}
    except Exception:
        error_logger.exception('Invalid agent payload for activity state | raw_agent=%s', agent)
        return jsonify({"error": "Invalid agent format"}), 400

    activity_logger.info(
        'LRS activity state served | state_id=%s | activity_id=%s | agent_present=%s | ip=%s',
        state_id,
        activity_id,
        bool(agent_data),
        _client_ip()
    )

    return jsonify({
        "stateId": state_id,
        "activityId": activity_id,
        "agent": agent_data
    })

@blp.route('/statements', methods=['PUT'])
@require_auth
def post_statement():
    try:
        statement_id = request.args.get("statementId")
        access_logger.info(
            'LRS statement received | method=PUT | statement_id=%s | ip=%s | content_type=%s',
            statement_id,
            _client_ip(),
            request.content_type
        )
        if request.content_type == 'application/json':
            statement_data = request.get_json() or {}
        else:
            statement_data = json.loads(request.data or b'{}')
        
        # # Extract statement components
        actor = statement_data.get('actor', {})
        verb = statement_data.get('verb', {})
        obj = statement_data.get('object', {})
        result = statement_data.get('result', {})
        context = statement_data.get('context', {})
        
        # Create new statement
        statement = Statement(
            actor_mbox=actor.get('mbox'),
            actor_name=actor.get('name'),
            verb_id=verb.get('id'),
            verb_display=verb.get('display', {}).get('en-US'),
            object_id=obj.get('id'),
            object_definition=json.dumps(obj.get('definition')) if obj.get('definition') else None,
            result_completion=result.get('completion'),
            result_success=result.get('success'),
            result_score_raw=result.get('score', {}).get('raw') if result.get('score') else None,
            result_score_min=result.get('score', {}).get('min') if result.get('score') else None,
            result_score_max=result.get('score', {}).get('max') if result.get('score') else None,
            result_score_scaled=result.get('score', {}).get('scaled') if result.get('score') else None,
            context_instructor=context.get('instructor'),
            context_team=context.get('team'),
            timestamp=datetime.fromisoformat(statement_data.get('timestamp').replace('Z', '+00:00')) if statement_data.get('timestamp') else lambda: datetime.now(tz=ZoneInfo("Asia/Kolkata")),
            authority=request.authorization.username if request.authorization else None,
            raw_statement=json.dumps(statement_data)
        )
        statement.save()
        # db.session.add(statement)
        
        # Add activity if it doesn't exist
        activity_id = obj.get('id')
        if activity_id:
            existing_activity = Activity.query.filter_by(id=activity_id).first()
            if not existing_activity:
                activity = Activity(
                    id=activity_id,
                    name=obj.get('definition', {}).get('name', {}).get('en-US'),
                    description=obj.get('definition', {}).get('description', {}).get('en-US'),
                    type=obj.get('definition', {}).get('type')
                )
                activity.save()
                # db.session.add(activity)
        
        # Add agent if it doesn't exist
        actor_mbox = actor.get('mbox')
        if actor_mbox:
            existing_agent = Agent.query.filter_by(mbox=actor_mbox).first()
            if not existing_agent:
                agent = Agent(
                    mbox=actor_mbox,
                    name=actor.get('name')
                )
                agent.save()
                # db.session.add(agent)

        # db.session.commit()
        
        # return jsonify([statement.id]), 200
        activity_logger.info(
            'LRS statement stored | statement_id=%s | actor=%s | verb=%s | object=%s | ip=%s',
            statement_id,
            actor.get('mbox'),
            verb.get('id'),
            obj.get('id'),
            _client_ip()
        )
        return jsonify([statement_id]), 200
        
    except Exception:
        db.session.rollback()
        error_logger.exception('Error storing LRS statement | statement_id=%s', request.args.get("statementId"))
        return jsonify({'error': 'Failed to process statement'}), 400
    

@blp.route('/statements', methods=['GET'])
@require_auth
def get_statements():
    try:
        # Parse query parameters
        agent_mbox = request.args.get('agent')
        verb_id = request.args.get('verb')
        activity_id = request.args.get('activity')
        since = request.args.get('since')
        until = request.args.get('until')
        limit = request.args.get('limit', 100, type=int)
        access_logger.info(
            'LRS statements query | agent=%s | verb=%s | activity=%s | since=%s | until=%s | limit=%s | ip=%s',
            agent_mbox,
            verb_id,
            activity_id,
            since,
            until,
            limit,
            _client_ip()
        )
        
        query = Statement.query.filter_by(voided=False)
        
        if agent_mbox:
            query = query.filter(Statement.actor_mbox == agent_mbox)
        if verb_id:
            query = query.filter(Statement.verb_id == verb_id)
        if activity_id:
            query = query.filter(Statement.object_id == activity_id)
        if since:
            since_date = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query = query.filter(Statement.timestamp >= since_date)
        if until:
            until_date = datetime.fromisoformat(until.replace('Z', '+00:00'))
            query = query.filter(Statement.timestamp <= until_date)
        
        statements = query.order_by(Statement.stored.desc()).limit(limit).all()

        activity_logger.info(
            'LRS statements returned | count=%d | limit=%s | ip=%s',
            len(statements),
            limit,
            _client_ip()
        )
        
        return jsonify({
            'statements': [stmt.to_dict() for stmt in statements],
            'more': len(statements) == limit
        }), 200
        
    except Exception:
        error_logger.exception('Error fetching LRS statements')
        return jsonify({'error': 'Failed to fetch statements'}), 400

@blp.route('/statements/<statement_id>', methods=['GET'])
@require_auth
def get_statement(statement_id):
    try:
        access_logger.info(
            'LRS statement fetch | statement_id=%s | ip=%s',
            statement_id,
            _client_ip()
        )
        statement = Statement.query.filter_by(id=statement_id, voided=False).first()
        if not statement:
            activity_logger.warning(
                'LRS statement not found | statement_id=%s | ip=%s',
                statement_id,
                _client_ip()
            )
            return jsonify({'error': 'Statement not found'}), 404
        
        activity_logger.info(
            'LRS statement served | statement_id=%s | ip=%s',
            statement_id,
            _client_ip()
        )
        return jsonify(statement.to_dict()), 200
        
    except Exception:
        error_logger.exception('Error fetching LRS statement | statement_id=%s', statement_id)
        return jsonify({'error': 'Failed to fetch statement'}), 400

@blp.route('/activities/<path:activity_id>', methods=['GET'])
@require_auth
def get_activity(activity_id):
    try:
        access_logger.info(
            'LRS activity fetch | activity_id=%s | ip=%s',
            activity_id,
            _client_ip()
        )
        activity = Activity.query.filter_by(id=activity_id).first()
        if not activity:
            activity_logger.warning(
                'LRS activity not found | activity_id=%s | ip=%s',
                activity_id,
                _client_ip()
            )
            return jsonify({'error': 'Activity not found'}), 404
        
        activity_logger.info(
            'LRS activity served | activity_id=%s | ip=%s',
            activity_id,
            _client_ip()
        )
        return jsonify({
            'id': activity.id,
            'definition': {
                'name': {'en-US': activity.name},
                'description': {'en-US': activity.description},
                'type': activity.type
            }
        }), 200
        
    except Exception:
        error_logger.exception('Error fetching LRS activity | activity_id=%s', activity_id)
        return jsonify({'error': 'Failed to fetch activity'}), 400

@blp.route('/about', methods=['GET'])
def about():
    access_logger.info(
        'LRS about requested | ip=%s',
        _client_ip()
    )
    return jsonify({
        'version': ['1.0.3'],
        'extensions': {}
    }), 200

# Web Interface Routes
@blp.route('/')
def index():
    total_statements = Statement.query.filter_by(voided=False).count()
    total_activities = Activity.query.count()
    total_agents = Agent.query.count()
    
    recent_statements = Statement.query.filter_by(voided=False).order_by(Statement.stored.desc()).limit(10).all()
    
    return render_template('index.html', 
                         total_statements=total_statements,
                         total_activities=total_activities,
                         total_agents=total_agents,
                         recent_statements=recent_statements)

@blp.route('/statements')
def statements():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    statements = Statement.query.filter_by(voided=False).order_by(Statement.stored.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('statements.html', statements=statements)

@blp.route('/activities')
def activities():
    activities = Activity.query.order_by(Activity.created_at.desc()).all()
    return render_template('activities.html', activities=activities)

@blp.route('/agents')
def agents():
    agents = Agent.query.order_by(Agent.created_at.desc()).all()
    return render_template('agents.html', agents=agents)

@blp.route('/statement/<statement_id>')
def statement_detail(statement_id):
    statement = Statement.query.filter_by(id=statement_id).first_or_404()
    return render_template('statement_detail.html', statement=statement)

# CORS support for SCORM packages
@blp.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Experience-API-Version')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@blp.route('/statements', methods=['OPTIONS'])
@blp.route('/activities/<path:activity_id>', methods=['OPTIONS'])
def handle_options():
    return '', 200
