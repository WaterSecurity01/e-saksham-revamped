from typing import List

from flask import Blueprint, current_app, flash, jsonify, redirect, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import joinedload

from app import db
from app.classes.helper import _build_enriched_options, admin_required, orm_to_dict_list
from app.classes.logging import get_route_loggers, _client_ip
from app.models import Block, Course, District, State_UT, UserCourse, User
from passlib.hash import pbkdf2_sha256

from app.models.activity_dashboard import (
    db,
    ActivityList,
    Cluster,
    Slope,
    Ridge,
    WaterWork,
    NatureOfWork,
    LocationSpecific,
    Category,
    Beneficiary,
    ActivityType,
    MajorScheduledCategory,
    WorkType,
    PermissibleWork,
)

blp = Blueprint('api', __name__, url_prefix='/api')

_loggers = get_route_loggers('api')
access_logger = _loggers.access
error_logger = _loggers.error
activity_logger = _loggers.activity

@blp.route("/states", methods=['GET'])
def states():
    access_logger.info(
        'API request | action=api.states | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    try:
        states = State_UT.query.all()
        state_list = [{"id": d.id, "name": d.name} for d in states]
        activity_logger.info('States fetched | count=%d | ip=%s', len(state_list), _client_ip())
        return jsonify(state_list), 200
    except Exception:
        error_logger.exception('Error fetching states list')
        return jsonify({'error': 'Unable to fetch states'}), 500

@blp.route("/districts")
def districts():
    state_id = request.args.get("state_id", type=int)

    if not state_id:
        return jsonify({"error": "state_id is required"}), 400
    access_logger.info(
        'API request | action=api.districts | method=%s | path=%s | ip=%s | state_id=%s',
        request.method,
        request.path,
        _client_ip(),
        state_id
    )
    try:
        district_list = [{"id": -1, "name": "--STATE OFFICIAL--"}]
        districts = District.query.filter_by(state_id=state_id).all()
        for d in districts:
            district_list.append({"id": d.id, "name": d.name})

        activity_logger.info(
            'Districts fetched | state_id=%s | count=%d | ip=%s',
            state_id,
            len(district_list),
            _client_ip()
        )
        return jsonify(district_list), 200
    except Exception:
        error_logger.exception('Error fetching districts | state_id=%s', state_id)
        return jsonify({'error': 'Unable to fetch districts'}), 500

@blp.route("/blocks")
def blocks():
    district_id = request.args.get("district_id", type=int)

    if not district_id:
        return jsonify({"error": "district_id is required"}), 400    
    access_logger.info(
        'API request | action=api.blocks | method=%s | path=%s | ip=%s | district_id=%s',
        request.method,
        request.path,
        _client_ip(),
        district_id
    )
    try:
        block_list = [{"id": -1, "name": "-- DISTRICT OFFICIAL --"}]
        if district_id == -1:
            block_list = [{"id": -1, "name": "-- STATE OFFICIAL --"}]
        else:
            blocks = Block.query.filter_by(district_id=district_id).all()
            for b in blocks:
                block_list.append({"id": b.id, "name": b.name})

        activity_logger.info(
            'Blocks fetched | district_id=%s | count=%d | ip=%s',
            district_id,
            len(block_list),
            _client_ip()
        )
        return jsonify(block_list), 200
    except Exception:
        error_logger.exception('Error fetching blocks | district_id=%s', district_id)
        return jsonify({'error': 'Unable to fetch blocks'}), 500

@blp.route('/decrypt_keys')
def decrypt_keys():
    # get your keys from wherever you store them
    access_logger.info(
        'API request | action=api.decrypt_keys | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    try:
        public_key = current_app.config.get('PUBLIC_KEY')
        if not public_key:
            activity_logger.warning('Public key missing in configuration | ip=%s', _client_ip())
            return jsonify({'error': 'Public key not configured'}), 500
        activity_logger.info('Public key served | ip=%s', _client_ip())
        return jsonify({'publicKey': public_key}), 200
    except Exception:
        error_logger.exception('Error retrieving public key')
        return jsonify({'error': 'Unable to retrieve public key'}), 500

@blp.route('/search-users')
@login_required
def api_search_users():
    """
    API endpoint for searching users with certification information.
    Returns: name, email, state, district, block, certification_status, certified_on
    """

    # Query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    search = request.args.get('search', '', type=str).strip()
    course_name = None

    access_logger.info(
        'API request | action=api.search_users | method=%s | path=%s | ip=%s | page=%s | per_page=%s | search=%s',
        request.method,
        request.path,
        _client_ip(),
        page,
        per_page,
        search
    )

    # Validate search term
    if len(search) < 3:
        activity_logger.warning(
            'Search term validation failed | search=%s | ip=%s',
            search,
            _client_ip()
        )
        return jsonify({
            'error': 'Search term must be at least 3 characters long',
            'users': [],
            'page': 1,
            'total_pages': 0,
            'total_users': 0
        }), 400

    try:
        base_query = (
            db.session.query(
                User,
                Course.name.label('course_name'),
                Course.short_name.label('course_short_name'),
                Course.id.label('course_id'),
                UserCourse.timestamp.label('certified_on')
            )
            .join(UserCourse, UserCourse.user_id == User.id)
            .join(Course, Course.id == UserCourse.course_id)
            .options(
                joinedload(User.state),
                joinedload(User.district),
                joinedload(User.block)
            )
            .filter(UserCourse.certificate_issued == True)
        )

        # Apply search filter for name and email
        search_pattern = f"%{search}%"
        base_query = base_query.filter(or_(
            User.name.ilike(search_pattern),
            User.email.ilike(search_pattern)
        ))

        # Apply state restriction for non-super admins
        if current_user.is_admin and '@esaksham.nic.in' not in current_user.email:
            user_state_id = current_user.state_id
            base_query = base_query.filter(User.state_id == user_state_id)

        # Order by name
        base_query = base_query.order_by(Course.name.asc(), User.name.asc())

        # Get total count before pagination
        total_users = base_query.count()

        # Pagination
        offset = (page - 1) * per_page
        results = base_query.offset(offset).limit(per_page).all()

        users = []
        for user_obj, course_name_row, course_short_name_row, course_id_row, certified_on in results:
            certified_date = certified_on.strftime('%Y-%m-%d') if certified_on else ""
            state_name = user_obj.state.name if user_obj.state else ""
            district_name = user_obj.district.name if user_obj.district else ""
            block_name = user_obj.block.name if user_obj.block else ""

            users.append({
                'id': user_obj.id,
                'uuid': user_obj.uuid,
                'name': user_obj.name,
                'email': user_obj.email,
                'state': state_name,
                'district': district_name,
                'block': block_name,
                'course_name': course_name_row,
                'course_short_name': course_short_name_row,
                'course_id': course_id_row,
                'certified_on': certified_date,
                'is_certified': True
            })

        total_pages = (total_users + per_page - 1) // per_page

        activity_logger.info(
            'Search complete | search=%s | returned=%d | total=%d | page=%d/%d | ip=%s',
            search,
            len(users),
            total_users,
            page,
            total_pages,
            _client_ip()
        )

        return jsonify({
            'users': users,
            'page': page,
            'total_pages': total_pages,
            'total_users': total_users,
            'search_term': search,
            'success': True,
            'course_name': course_name
        })

    except Exception:
        error_logger.exception('Error searching users | search=%s', search)
        return jsonify({
            'error': 'An error occurred while searching users',
            'users': [],
            'page': 1,
            'total_pages': 0,
            'total_users': 0,
            'success': False
        }), 500
        
@blp.route('/charts_dashboard_data', methods=['post'])
def charts_dashboard_data():
    data = request.get_json(silent=True) or {}
    if not data:
        activity_logger.warning(
            'Dashboard data request missing body | method=%s | path=%s | ip=%s',
            request.method,
            request.path,
            _client_ip()
        )
        return jsonify({'error': 'Request body must be JSON'}), 400
    access_logger.info(
        'API request | action=api.charts_dashboard_data | method=%s | path=%s | ip=%s | payload_keys=%s',
        request.method,
        request.path,
        _client_ip(),
        sorted(list(data.keys()))
    )
    try:
        total_users = User.get_total_users(state_id=data['state_id'], district_id=data['district_id'], block_id=data['block_id'])
        certified_users = UserCourse.get_certified_users(state_id=data['state_id'], district_id=data['district_id'], block_id=data['block_id'])
        issuance_percentage = (certified_users / total_users * 100) if total_users > 0 else 0
        card_data = {
            'total_users': total_users,
            'certified_users': certified_users,
            'issuance_percentage': f"{issuance_percentage:.2f}"
        }

        pie_chart_data = {
            'issued_total': certified_users,
            'non_issued_total': total_users - certified_users
        }

        activity_logger.info(
            'Dashboard data computed | state=%s | district=%s | block=%s | total_users=%s | certified=%s | ip=%s',
            data.get('state_id'),
            data.get('district_id'),
            data.get('block_id'),
            total_users,
            certified_users,
            _client_ip()
        )

        return jsonify({'card_data': card_data, 'pie_chart_data': pie_chart_data}),200
    except Exception:
        error_logger.exception(
            'Error computing dashboard data | state=%s | district=%s | block=%s',
            data.get('state_id'),
            data.get('district_id'),
            data.get('block_id')
        )
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500
    
    
@blp.route('/users')
@login_required
@admin_required
def api_users():
    # Query params
    page         = request.args.get('page', 1, type=int)
    per_page     = min(request.args.get('per_page', 100, type=int), 500)
    search       = request.args.get('search', '', type=str).strip()
    status       = request.args.get('status', 'all')
    admin        = request.args.get('admin', 'all')
    sort_by      = request.args.get('sort_by', 'name')
    sort_dir     = request.args.get('sort_dir', 'asc')
    state_id     = request.args.get('state_id', type=int)
    district_id  = request.args.get('district_id', type=int)
    block_id     = request.args.get('block_id', type=int)
    certificate_issued = request.args.get('certificate_issued',type=int)

    access_logger.info(
        'API request | action=api.users | method=%s | path=%s | ip=%s | page=%s | per_page=%s | search=%s | status=%s | admin=%s',
        request.method,
        request.path,
        _client_ip(),
        page,
        per_page,
        search,
        status,
        admin
    )

    try:
        # Whitelist for sorting
        sortable_columns = {
            'name': User.name,
            'email': User.email,
            'registered_on': User.registered_on
        }
        sort_column = sortable_columns.get(sort_by, User.name)
        sort_column = desc(sort_column) if sort_dir == 'desc' else asc(sort_column)

        # Base query with eager loading to avoid N+1
        query = (User.query
                 .options(
                     joinedload(User.state),    # relationship names from your model
                     joinedload(User.district),
                     joinedload(User.block)
                 ))
        if certificate_issued:
            query = query.join(UserCourse,UserCourse.user_id == User.id)
        # Filters
        if status != 'all':
            query = query.filter(User.is_active == (status == 'active'))
        if admin != 'all':
            query = query.filter(User.is_admin == (admin == 'admin'))

        if state_id:
            query = query.filter(User.state_id == state_id)
        if district_id:
            query = query.filter(User.district_id == district_id)
        if block_id:
            query = query.filter(User.block_id == block_id)

        if not certificate_issued:
            if current_user.is_admin:
                if '@esaksham.nic.in' not in current_user.email:
                    user_state_id = current_user.state_id
                    query = query.filter(User.state_id == user_state_id)

        if search:
            pattern = f"%{search}%"
            query = query.filter(or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern)
            ))

        query = query.order_by(sort_column)

        users_page = query.paginate(page=page, per_page=per_page, error_out=False)

        # Build response list
        users = []
        for u in users_page.items:
            # State_UT earlier code referenced .short_name; fall back to .name if not present.
            state_val = ''
            if u.state:
                state_val = getattr(u.state, 'short_name', None) or getattr(u.state, 'name', '') or ''
            district_val = u.district.name if u.district else ''
            block_val = u.block.name if u.block else ''

            users.append({
                'id': u.id,
                'uuid': u.uuid,
                'name': u.name,
                'email': u.email,
                'registered_on': u.registered_on.strftime('%Y-%m-%d %H:%M:%S') if u.registered_on else '',
                'is_active': u.is_active,
                'is_admin': u.is_admin,
                'state': state_val,
                'district': district_val,
                'block': block_val
            })

        activity_logger.info(
            'Users listing retrieved | total=%d | page=%d/%d | filters={state:%s,district:%s,block:%s,search:%s} | ip=%s',
            users_page.total,
            users_page.page,
            users_page.pages,
            state_id,
            district_id,
            block_id,
            search,
            _client_ip()
        )

        return jsonify({
            'users': users,
            'page': users_page.page,
            'total_pages': users_page.pages,
            'total_users': users_page.total
        })
    except Exception:
        error_logger.exception(
            'Error retrieving users | state=%s | district=%s | block=%s | search=%s',
            state_id,
            district_id,
            block_id,
            search
        )
        return jsonify({'error': 'Failed to fetch users'}), 500
    
@blp.route('/toggle-admin/<uuid>')
@login_required
@admin_required
def api_toggle_admin(uuid):
    access_logger.info(
        'API request | action=api.toggle_admin | method=%s | path=%s | ip=%s | target_uuid=%s | actor_id=%s',
        request.method,
        request.path,
        _client_ip(),
        uuid,
        getattr(current_user, 'id', None)
    )
    try:
        user = User.query.filter_by(uuid=uuid).first_or_404()
        user.is_admin = not user.is_admin
        db.session.commit()
        activity_logger.info(
            'Admin status toggled | target_user=%s | is_admin=%s | actor_id=%s | ip=%s',
            user.email,
            user.is_admin,
            getattr(current_user, 'id', None),
            _client_ip()
        )
        return jsonify({'success': True, 'is_admin': user.is_admin})
    except Exception:
        db.session.rollback()
        error_logger.exception('Error toggling admin status | user_uuid=%s', uuid)
        return jsonify({'success': False, 'message': 'Failed to toggle admin status'}), 500

@blp.route('/toggle-user-status/<string:user_uuid>', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_uuid):
    access_logger.info(
        'API request | action=api.toggle_user_status | method=%s | path=%s | ip=%s | target_uuid=%s | actor_id=%s',
        request.method,
        request.path,
        _client_ip(),
        user_uuid,
        getattr(current_user, 'id', None)
    )
    try:
        data = request.get_json()
        is_active = data.get('is_active', False)
        user = User.query.filter_by(uuid=user_uuid).first_or_404()
        user.is_active = is_active
        db.session.commit()
        activity_logger.info(
            'User status toggled | target_user=%s | is_active=%s | actor_id=%s | ip=%s',
            user.email,
            is_active,
            getattr(current_user, 'id', None),
            _client_ip()
        )
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        error_logger.exception('Error toggling user status | user_uuid=%s', user_uuid)
        return jsonify({'success': False, 'message': 'Failed to toggle user status'}), 500

@blp.route('/reset-password/<string:user_uuid>', methods=['POST'])
@login_required
@admin_required
def reset_password(user_uuid):
    access_logger.info(
        'API request | action=api.reset_password | method=%s | path=%s | ip=%s | target_uuid=%s | actor_id=%s',
        request.method,
        request.path,
        _client_ip(),
        user_uuid,
        getattr(current_user, 'id', None)
    )
    try:
        user = User.query.filter_by(uuid=user_uuid).first_or_404()
        default_password = str.upper(user.email[0]) + user.email[1:4] + '_123@'
        user.password = pbkdf2_sha256.hash(default_password)
        db.session.commit()
        activity_logger.info(
            'Password reset | target_user=%s | actor_id=%s | ip=%s',
            user.email,
            getattr(current_user, 'id', None),
            _client_ip()
        )
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        error_logger.exception('Error resetting password | user_uuid=%s', user_uuid)
        return jsonify({'success': False, 'message': 'Failed to reset password'}), 500


@blp.route('/delete-user/<string:user_uuid>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_uuid):
    access_logger.info(
        'API request | action=api.delete_user | method=%s | path=%s | ip=%s | target_uuid=%s | actor_id=%s',
        request.method,
        request.path,
        _client_ip(),
        user_uuid,
        getattr(current_user, 'id', None)
    )
    user = User.query.filter_by(uuid=user_uuid).first_or_404()
    try:
        db.session.delete(user)
        db.session.commit()
        activity_logger.info(
            'User deleted | target_user=%s | actor_id=%s | ip=%s',
            user.email,
            getattr(current_user, 'id', None),
            _client_ip()
        )
        flash(f'User {user.name} deleted Successfully', 'success')
    except Exception as e:
        db.session.rollback()
        error_logger.exception('Error deleting user | user_uuid=%s', user_uuid)
        flash(f'Error deleting user {user.name}: {e}', 'error')
    return redirect(url_for('admin.user_management'))


@blp.route('/update_completion', methods=['POST'])
@login_required
@admin_required
def update_completion():
    """
    Receives a list of users and updates their completion status.
    """
    access_logger.info(
        'API request | action=api.update_completion | method=%s | path=%s | ip=%s | actor_id=%s',
        request.method,
        request.path,
        _client_ip(),
        getattr(current_user, 'id', None)
    )
    course_id = None
    try:
        payload = request.get_json() or {}
        course_id = payload.get('course_id')
        users = payload.get('users')

        if not course_id:
            activity_logger.warning(
                'Completion update missing course_id | ip=%s',
                _client_ip()
            )
            return jsonify({'message': 'course_id is required'}), 400

        if not isinstance(users, list):
            activity_logger.warning(
                'Completion update invalid payload | course_id=%s | ip=%s',
                course_id,
                _client_ip()
            )
            return jsonify({'message': 'Invalid data format'}), 400

        updated_count = 0
        for user_data in users:
            email = user_data.get('email')
            if not email:
                continue
            user = User.query.filter_by(email=email).first()
            if not user:
                continue

            user_course = UserCourse.query.filter_by(user_id=user.id, course_id=course_id).first()
            if user_course:
                if not user_course.certificate_issued:
                    user_course.certificate_issued = True
                    db.session.add(user_course)
                    updated_count += 1
            else:
                db.session.add(UserCourse(user.id, course_id, True))
                updated_count += 1

        db.session.commit()

        activity_logger.info(
            'Completion status updated | course_id=%s | users_processed=%d | actor_id=%s | ip=%s',
            course_id,
            len(users),
            getattr(current_user, 'id', None),
            _client_ip()
        )

        return jsonify({'message': 'Data updated successfully.', 'updated': updated_count}), 200

    except Exception:
        db.session.rollback()
        error_logger.exception('Error updating completion status | course_id=%s', course_id)
        return jsonify({'message': 'An internal server error occurred.'}), 500
    
@blp.route("/get_users_certificate")
@login_required
@admin_required
def get_users():
    access_logger.info(
        'API request | action=api.get_users_certificate | method=%s | path=%s | ip=%s | actor_id=%s | params=%s',
        request.method,
        request.path,
        _client_ip(),
        getattr(current_user, 'id', None),
        dict(request.args)
    )
    try:
        course_id = request.args.get('course_id', type=int)
        if not course_id:
            activity_logger.warning(
                'Certificate user request missing course_id | ip=%s | actor_id=%s',
                _client_ip(),
                getattr(current_user, 'id', None)
            )
            return jsonify({"error": "course_id is required"}), 400

        is_developer = ("@esaksham.nic.in" in current_user.email)

        if is_developer:
            # Matches get_untracked_user_course_developer() selected columns
            rows = UserCourse.get_untracked_user_course_developer(course_id)
            payload = [
                {
                    "name": getattr(r, "name", "") or "",
                    "email": getattr(r, "email", "") or "",
                    "is_completed": False,
                    # Geo IDs
                    "state_id": getattr(r, "state_id", None),
                    "district_id": getattr(r, "district_id", None),
                    "block_id": getattr(r, "block_id", None),
                    # Geo names
                    "state_short_name": getattr(r, "state_short_name", "") or "",
                    "state_name": getattr(r, "state_name", "") or "",
                    "district_name": getattr(r, "district_name", "") or "",
                    "block_name": getattr(r, "block_name", "") or "",
                }
                for r in rows
            ]
            return jsonify(payload), 200

        # Non-developer: scope by user's state and return minimal fields
        user = User.get_user_by_id(current_user.id)  # expected dict-like
        if not user or not user.get("state_id"):
            return jsonify({"error": "There was an internal server error"}), 500

        users = UserCourse.get_untracked_user_course(user["state_id"], course_id)
        payload = [
            {
                "name": getattr(u, "name", "") or "",
                "email": getattr(u, "email", "") or "",
                "is_completed": False,
            }
            for u in users
        ]
        activity_logger.info(
            'Certificate user listing retrieved | course_id=%s | count=%d | developer=%s | actor_id=%s | ip=%s',
            course_id,
            len(payload),
            is_developer,
            getattr(current_user, 'id', None),
            _client_ip()
        )
        return jsonify(payload), 200

    except Exception:
        error_logger.exception('Error fetching certificate users | params=%s', dict(request.args))
        return jsonify({"error": "Internal server error"}), 500
    
    
@blp.route('/activity_identification/filter', methods=['POST'])
@login_required
def activity_identification_filter():
    """
    Enhanced filtering with checkbox support and auto-selection logic
    """
    try:
        data = request.get_json() or {}
        access_logger.info(
            'API request | action=api.activity_identification_filter | method=%s | path=%s | ip=%s | actor_id=%s | payload_keys=%s',
            request.method,
            request.path,
            _client_ip(),
            getattr(current_user, 'id', None),
            sorted(list(data.keys()))
        )

        # Filter map
        filter_map = {
            "clusters": ActivityList.cluster_type,
            "categories": ActivityList.category,
            "major_scheduled_category": ActivityList.major_scheduled_category,
            "beneficiaries": ActivityList.beneficiary_type,
            "activity_types": ActivityList.activity_type,
            "work_types": ActivityList.work_type,
            "slopes": ActivityList.slope,
            "ridges": ActivityList.ridge,
            "water_works": ActivityList.water_work,
            "location_specifics": ActivityList.location_specifics,
            "permissible_works": ActivityList.permissible_work,
            "nature_of_works": ActivityList.nature_of_work,
        }

        # Apply filters
        filtered_q = db.session.query(ActivityList)
        for arg_name, column in filter_map.items():
            ids = data.get(arg_name, [])
            if ids and len(ids) > 0:
                filtered_q = filtered_q.filter(column.in_(ids))

        # Get distinct IDs from filtered query
        filtered_ids = {
            key: set(row[0] for row in filtered_q.with_entities(col).distinct().all() if row[0] is not None)
            for key, col in filter_map.items()
        }

        # Model mapping
        model_map = {
            "clusters": (Cluster, ["id", "name"]),
            "categories": (Category, ["id", "name"]),
            "major_scheduled_category": (MajorScheduledCategory, ["id", "name"]),
            "beneficiaries": (Beneficiary, ["id", "name"]),
            "activity_types": (ActivityType, ["id", "short_name"]),
            "work_types": (WorkType, ["id", "name"]),
            "slopes": (Slope, ["id", "name"]),
            "ridges": (Ridge, ["id", "name"]),
            "water_works": (WaterWork, ["id", "name"]),
            "location_specifics": (LocationSpecific, ["id", "name"]),
            "permissible_works": (PermissibleWork, ["id", "name"]),
            "nature_of_works": (NatureOfWork, ["id", "short_name"]),
        }

        # Define which groups are radio buttons (yuktdhara-card entities)
        yuktdhara_groups = {
            "nature_of_works", "categories", "major_scheduled_category", 
            "beneficiaries", "activity_types", "work_types", "permissible_works"
        }
        
        # Define which groups are checkboxes (multi-select)
        checkbox_groups = {
            "clusters", "slopes", "ridges", "water_works", "location_specifics"
        }

        reorder_on_disable = {"location_specifics", "major_scheduled_category", "work_types", "permissible_works"}
        response_data = {}
        auto_select_data = {}
        single_select_auto_fill = {}

        has_active_filters = any(
            isinstance(ids, (list, tuple, set)) and len(ids) > 0
            for ids in data.values()
        )

        permissible_filter_active = bool(data.get("permissible_works"))

        for key, (model, fields) in model_map.items():
            all_options = orm_to_dict_list(model.query.order_by(model.id).all(), fields)
            
            enriched = []
            enabled_count = 0
            enabled_options = []

            for opt in all_options:
                opt_id = opt["id"]
                is_disabled = opt_id not in filtered_ids.get(key, set())
                opt["disabled"] = is_disabled

                if not is_disabled:
                    enabled_count += 1
                    enabled_options.append(opt)

                enriched.append(opt)

            # Auto-select checkbox groups based on rules
            if key in checkbox_groups:
                selected_ids: List[int] = []

                if key == "slopes":
                    if permissible_filter_active and enabled_count == 6:
                        selected_ids = [7]
                        for opt in enriched:
                            if opt["id"] == 7:
                                opt["disabled"] = False
                            elif opt["id"] in {1, 2, 3, 4, 5, 6}:
                                opt["disabled"] = True
                        enabled_options = [opt for opt in enriched if not opt["disabled"]]
                        enabled_count = len(enabled_options)
                    elif permissible_filter_active and enabled_count == 1 and enabled_options[0]["id"] == 7:
                        selected_ids = [7]
                    elif permissible_filter_active and enabled_count > 0:
                        slope_enabled_ids = {opt["id"] for opt in enabled_options}
                        any_slope_option = next((opt for opt in enriched if opt["id"] == 7), None)

                        slope_condition = all(sid in slope_enabled_ids for sid in [1, 2, 3, 4, 5, 6])

                        if any_slope_option and not any_slope_option["disabled"] and slope_condition:
                            selected_ids = [7]
                        else:
                            selected_ids = [opt["id"] for opt in enabled_options]
                    elif enabled_count == 1 and not data.get(key):
                        selected_ids = [enabled_options[0]["id"]]
                else:
                    if permissible_filter_active and enabled_count > 0:
                        selected_ids = [opt["id"] for opt in enabled_options]
                    elif enabled_count == 1 and not data.get(key):
                        selected_ids = [enabled_options[0]["id"]]

                if selected_ids:
                    auto_select_data[key] = selected_ids

            # Single selection auto-fill for yuktdhara-card fields only
            elif key in yuktdhara_groups and enabled_count == 1 and not data.get(key):
                single_select_auto_fill[key] = {
                    'id': enabled_options[0]['id'],
                    'name': enabled_options[0][fields[1]]
                }

            # Sorting logic
            if key in reorder_on_disable:
                enriched.sort(key=lambda x: (x["disabled"], x["id"]))
            else:
                enriched.sort(key=lambda x: x["id"])

            response_data[key] = enriched
            response_data[f"{key}_count"] = enabled_count

        # Add auto-selection data
        if auto_select_data:
            response_data["auto_select"] = auto_select_data

        if single_select_auto_fill:
            response_data["auto_fill"] = single_select_auto_fill


        activity_logger.info(
            'Activity identification filter computed | actor_id=%s | ip=%s | auto_select_keys=%s',
            getattr(current_user, 'id', None),
            _client_ip(),
            sorted(list((auto_select_data or {}).keys()))
        )

        return jsonify({
            "success": True,
            "data": response_data
        })

    except Exception:
        error_logger.exception('Error in activity identification filter')
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@blp.route('/activity_identification/search', methods=['POST'])
@login_required
def activity_identification_search():
    """Search permissible works and surface related options for quick filtering."""

    try:
        data = request.get_json() or {}
        search_term = data.get('search', '').strip().lower()
        access_logger.info(
            'API request | action=api.activity_identification_search | method=%s | path=%s | ip=%s | search=%s',
            request.method,
            request.path,
            _client_ip(),
            search_term
        )

        if not search_term or len(search_term) < 3:
            activity_logger.warning(
                'Activity identification search validation failed | search=%s | ip=%s',
                search_term,
                _client_ip()
            )
            return jsonify({
                "success": False,
                "error": "Search term must be at least 3 characters"
            })

        matching_permissible_works = PermissibleWork.query.filter(
            PermissibleWork.name.ilike(f'%{search_term}%')
        ).order_by(PermissibleWork.id).all()

        matching_pw_ids = [pw.id for pw in matching_permissible_works]

        if not matching_pw_ids:
            # Nothing matched – return fully disabled option sets so UI can indicate no hits
            return jsonify({
                "success": True,
                "data": {
                    "permissible_work_ids": [],
                    "permissible_works": _build_enriched_options(PermissibleWork, {"id", "name"}, set()),
                    "work_types": _build_enriched_options(WorkType, {"id", "name"}, set()),
                    "major_scheduled_category": _build_enriched_options(MajorScheduledCategory, {"id", "name"}, set())
                }
            })

        related_activities = ActivityList.query.filter(
            ActivityList.permissible_work.in_(matching_pw_ids)
        ).all()

        work_type_ids = {
            activity.work_type for activity in related_activities if activity.work_type is not None
        }

        major_scheduled_ids = {
            activity.major_scheduled_category
            for activity in related_activities
            if activity.major_scheduled_category is not None
        }

        response_payload = {
            "permissible_work_ids": matching_pw_ids,
            "permissible_works": _build_enriched_options(
                PermissibleWork,
                {"id", "name"},
                set(matching_pw_ids)
            ),
            "work_types": _build_enriched_options(
                WorkType,
                {"id", "name"},
                work_type_ids
            ),
            "major_scheduled_category": _build_enriched_options(
                MajorScheduledCategory,
                {"id", "name"},
                major_scheduled_ids
            )
        }

        activity_logger.info(
            'Activity identification search results ready | search=%s | matches=%d | ip=%s',
            search_term,
            len(matching_pw_ids),
            _client_ip()
        )

        return jsonify({
            "success": True,
            "data": response_payload
        })

    except Exception:
        error_logger.exception('Error searching activity identification | payload=%s', data if 'data' in locals() else {})
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500
