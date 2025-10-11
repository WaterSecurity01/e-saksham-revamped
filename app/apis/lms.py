from datetime import datetime

from flask import Blueprint, jsonify, request, session
from flask_login import current_user

from app.classes.logging import get_route_loggers, _client_ip
from app.db import db
from app.models import ScormData
from app.models.user_courses import UserCourse

blp = Blueprint('api_lms', __name__, url_prefix='/api/lms')

_loggers = get_route_loggers('api_lms')
access_logger = _loggers.access
error_logger = _loggers.error
activity_logger = _loggers.activity

@blp.route('/scorm/<int:course_id>/initialize', methods=['POST'])
def scorm_initialize(course_id):
    """Initialize SCORM session - should return true/false, not suspend_data"""
    try:
        access_logger.info(
            'SCORM initialize request | course_id=%s | ip=%s | user_id=%s',
            course_id,
            _client_ip(),
            getattr(current_user, 'id', None)
        )
        # Check if user has existing progress
        user_id = getattr(current_user, 'id', None)
        if not user_id:
            activity_logger.warning(
                'SCORM initialize failed | reason=no_user | course_id=%s | ip=%s',
                course_id,
                _client_ip()
            )
            return jsonify({'result': 'false', 'errorCode': '101'})  # No current user session
        
        # Initialize session state
        session[f'scorm_{course_id}_initialized'] = True
        activity_logger.info(
            'SCORM session initialised | user_id=%s | course_id=%s | ip=%s',
            user_id,
            course_id,
            _client_ip()
        )
        return jsonify({'result': 'true', 'errorCode': '0'})
    except Exception:
        error_logger.exception('SCORM initialize error | course_id=%s', course_id)
        return jsonify({'result': 'false', 'errorCode': '101'}) 

# flask backend:
@blp.route('/scorm/<int:course_id>/get_value', methods=['POST'])
def scorm_get_value(course_id):
    """Get SCORM data value"""
    try:
        data = request.get_json() or {}
        access_logger.info(
            'SCORM get_value request | course_id=%s | cmi_element=%s | ip=%s | user_id=%s',
            course_id,
            data.get('element'),
            _client_ip(),
            getattr(current_user, 'id', None)
        )
        cmi_key = data.get('element', '')
        user_id = getattr(current_user, 'id', None)
        if not user_id:
            activity_logger.warning(
                'SCORM get_value failed | reason=no_user | course_id=%s | element=%s | ip=%s',
                course_id,
                cmi_key,
                _client_ip()
            )
            return jsonify({'result': '', 'errorCode': '101'})
        result = ScormData.get_by_key(user_id, course_id, cmi_key)
        if result: 
            activity_logger.info(
                'SCORM value retrieved | user_id=%s | course_id=%s | element=%s | ip=%s',
                user_id,
                course_id,
                cmi_key,
                _client_ip()
            )
            return jsonify({'result': result.cmi_value, 'errorCode': '0'})
        else:
            activity_logger.info(
                'SCORM value missing | user_id=%s | course_id=%s | element=%s | ip=%s',
                user_id,
                course_id,
                cmi_key,
                _client_ip()
            )
            return jsonify({'result': '', 'errorCode': '101'})

    except Exception:
        error_logger.exception('SCORM get_value error | course_id=%s', course_id)
        return jsonify({'result': '', 'errorCode': '101'})

@blp.route('/scorm/<int:course_id>/set_value', methods=['POST'])
def scorm_set_value(course_id):
    """Set SCORM data value"""
    try:
        data = request.get_json() or {}
        cmi_key = data.get('element', '')
        cmi_value = data.get('value', '')
        user_id = getattr(current_user, 'id', None)

        access_logger.info(
            'SCORM set_value request | course_id=%s | element=%s | ip=%s | user_id=%s',
            course_id,
            cmi_key,
            _client_ip(),
            user_id
        )

        if not user_id:
            activity_logger.warning(
                'SCORM set_value failed | reason=no_user | course_id=%s | element=%s | ip=%s',
                course_id,
                cmi_key,
                _client_ip()
            )
            return jsonify({'result': 'false', 'errorCode': '101'})
        
        if not session.get(f'scorm_{course_id}_initialized'):
            activity_logger.warning(
                'SCORM set_value failed | reason=not_initialized | user_id=%s | course_id=%s | element=%s | ip=%s',
                user_id,
                course_id,
                cmi_key,
                _client_ip()
            )
            return jsonify({'result': 'false', 'errorCode': '132'})  # Not initialized
        
        # Validate required elements
        if not cmi_key:
            activity_logger.warning(
                'SCORM set_value failed | reason=invalid_argument | user_id=%s | course_id=%s | ip=%s',
                user_id,
                course_id,
                _client_ip()
            )
            return jsonify({'result': 'false', 'errorCode': '201'})  # Invalid argument
    
        # Save or update data
        scorm_data = ScormData.get_by_key(user_id, course_id, cmi_key)
        if scorm_data:
            scorm_data.cmi_value = cmi_value
            scorm_data.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            scorm_data.update()
        else:
            scorm_data = ScormData(
                user_id=user_id,
                course_id=course_id,
                cmi_key=cmi_key,
                cmi_value=cmi_value
            )
            scorm_data.save()
        if cmi_key == 'cmi.core.lesson_status':
            if cmi_value == 'passed':
                # update certification in user_course to true
                if not UserCourse.update(user_id=user_id, course_id=course_id):
                    db.session.rollback()
                    return jsonify({'result': 'false', 'errorCode': '101'})
        activity_logger.info(
            'SCORM set_value success | user_id=%s | course_id=%s | element=%s | ip=%s',
            user_id,
            course_id,
            cmi_key,
            _client_ip()
        )
        return jsonify({'result': 'true', 'errorCode': '0'})
        
    except Exception:
        db.session.rollback()
        error_logger.exception('SCORM set_value error | course_id=%s | element=%s', course_id, locals().get('cmi_key'))
        return jsonify({'result': 'false', 'errorCode': '101'})

@blp.route('/scorm/<int:course_id>/commit', methods=['POST'])
def scorm_commit(course_id):
    """Commit SCORM data to persistent storage"""
    try:
        access_logger.info(
            'SCORM commit request | course_id=%s | ip=%s | user_id=%s',
            course_id,
            _client_ip(),
            getattr(current_user, 'id', None)
        )
        if not session.get(f'scorm_{course_id}_initialized'):
            activity_logger.warning(
                'SCORM commit failed | reason=not_initialized | course_id=%s | user_id=%s | ip=%s',
                course_id,
                getattr(current_user, 'id', None),
                _client_ip()
            )
            return jsonify({'result': 'false', 'errorCode': '132'})  # Not initialized
        
        # Force commit any pending database changes
        db.session.commit()
        activity_logger.info(
            'SCORM commit success | course_id=%s | user_id=%s | ip=%s',
            course_id,
            getattr(current_user, 'id', None),
            _client_ip()
        )
        return jsonify({'result': 'true', 'errorCode': '0'})
        
    except Exception:
        error_logger.exception('SCORM commit error | course_id=%s', course_id)
        return jsonify({'result': 'false', 'errorCode': '101'})

@blp.route('/scorm/<int:course_id>/finish', methods=['POST'])
def scorm_finish(course_id):
    """Finish SCORM session"""
    try:
        access_logger.info(
            'SCORM finish request | course_id=%s | ip=%s | user_id=%s',
            course_id,
            _client_ip(),
            getattr(current_user, 'id', None)
        )
        if not session.get(f'scorm_{course_id}_initialized'):
            activity_logger.warning(
                'SCORM finish failed | reason=not_initialized | user_id=%s | course_id=%s | ip=%s',
                getattr(current_user, 'id', None),
                course_id,
                _client_ip()
            )
            return jsonify({'result': 'false', 'errorCode': '132'})  # Not initialized
        
        # Commit any final data
        db.session.commit()
        
        # Clear session state
        session.pop(f'scorm_{course_id}_initialized', None)
        
        activity_logger.info(
            'SCORM session finished | user_id=%s | course_id=%s | ip=%s',
            getattr(current_user, 'id', None),
            course_id,
            _client_ip()
        )

        return jsonify({'result': 'true', 'errorCode': '0'})
        
    except Exception:
        error_logger.exception('SCORM finish error | course_id=%s', course_id)
        return jsonify({'result': 'false', 'errorCode': '101'})

@blp.route('/scorm/<int:course_id>/get_last_error', methods=['POST'])
def scorm_get_last_error(course_id):
    """Get last error code"""
    access_logger.info(
        'SCORM get_last_error request | course_id=%s | ip=%s | user_id=%s',
        course_id,
        _client_ip(),
        getattr(current_user, 'id', None)
    )
    return jsonify({'result': '0', 'errorCode': '0'})

@blp.route('/scorm/<int:course_id>/get_error_string', methods=['POST'])
def scorm_get_error_string(course_id):
    """Get error string for error code"""
    data = request.get_json() or {}
    access_logger.info(
        'SCORM get_error_string request | course_id=%s | error_code=%s | ip=%s | user_id=%s',
        course_id,
        data.get('errorCode'),
        _client_ip(),
        getattr(current_user, 'id', None)
    )
    error_code = data.get('errorCode', '0')
    
    error_strings = {
        '0': 'No Error',
        '101': 'General Exception',
        '132': 'LMS Not Initialized',
        '201': 'Invalid Argument Error'
    }
    
    return jsonify({'result': error_strings.get(error_code, 'Unknown Error'), 'errorCode': '0'})

@blp.route('/scorm/<int:course_id>/get_diagnostic', methods=['POST'])
def scorm_get_diagnostic(course_id):
    """Get diagnostic information"""
    access_logger.info(
        'SCORM get_diagnostic request | course_id=%s | ip=%s | user_id=%s',
        course_id,
        _client_ip(),
        getattr(current_user, 'id', None)
    )
    return jsonify({'result': '', 'errorCode': '0'})
