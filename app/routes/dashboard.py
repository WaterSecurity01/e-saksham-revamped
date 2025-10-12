from collections import defaultdict
from typing import List

from flask import Blueprint, json, jsonify, render_template, request
from flask_login import login_required

from app.classes.helper import orm_to_dict_list
from app.classes.logging import get_route_loggers , _client_ip
from app.models.user import User
from app.models.user_courses import UserCourse

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

_loggers = get_route_loggers('dashboard')
access_logger = _loggers.access
error_logger = _loggers.error
activity_logger = _loggers.activity


blp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@blp.route('/')
def universal_dashboard():
    access_logger.info(
        'Route accessed | action=universal_dashboard | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    try:
        return render_template("dashboard/universal_dashboard.html")
    except Exception:
        error_logger.exception('Error rendering universal dashboard view')
        raise

@blp.route('/charts')
@login_required
def charts():
    access_logger.info(
        'Route accessed | action=charts | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    try:
        total_users = User.get_total_users()
        certified_users = UserCourse.get_certified_users()
        issuance_percentage = (certified_users / total_users * 100) if total_users > 0 else 0
        card_data = {
            'total_users': total_users,
            'certified_users': certified_users,
            'issuance_percentage': f"{issuance_percentage:.2f}"
        }

        activity_logger.info(
            'Computed card data for charts | total_users=%d | certified_users=%d | issuance_percentage=%s',
            total_users,
            certified_users,
            card_data['issuance_percentage']
        )

        pie_chart_data = {
            'issued_total': certified_users,
            'non_issued_total': total_users - certified_users
        }

        states = UserCourse.get_state_wise_users(top_5=True)
        districts = UserCourse.get_all_district_wise_users([s['id'] for s in states], top_5=True)
        blocks = UserCourse.get_all_block_wise_users([d['id'] for d in districts], top_5=True)
        users = UserCourse.get_all_users_in_blocks([b['id'] for b in blocks])

        district_data = defaultdict(list)
        for d in districts:
            district_data[d['state_id']].append(d)

        block_data = defaultdict(list)
        for b in blocks:
            block_data[b['district_id']].append(b)

        users_data = defaultdict(list)
        for u in users:
            users_data[u['block_id']].append(u)

        bar_chart_data = {
            'states': states,
            'districts': dict(district_data),
            'blocks': dict(block_data),
            'users': dict(users_data),
        }

        activity_logger.info(
            'Prepared chart hierarchy | states=%d | districts=%d | blocks=%d | users=%d',
            len(states),
            len(districts),
            len(blocks),
            len(users)
        )

        return render_template(
            'dashboard/charts_dashboard.html',
            card_data=card_data,
            pie_chart_data=pie_chart_data,
            bar_chart_data=bar_chart_data
        )
    except Exception:
        error_logger.exception('Error while preparing dashboard charts data')
        raise



@blp.route('/drill_chart')
@login_required
def drill_chart():
    access_logger.info(
        'Route accessed | action=drill_chart | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    try:

        states = UserCourse.get_state_wise_users()
        districts = UserCourse.get_all_district_wise_users([s['id'] for s in states] )
        blocks = UserCourse.get_all_block_wise_users([d['id'] for d in districts] )
        users = UserCourse.get_all_users_in_blocks([b['id'] for b in blocks])

        district_data = defaultdict(list)
        for d in districts:
            district_data[d['state_id']].append(d)

        block_data = defaultdict(list)
        for b in blocks:
            block_data[b['district_id']].append(b)

        users_data = defaultdict(list)
        for u in users:
            users_data[u['block_id']].append(u)

        bar_chart_data = {
            'states': states,
            'districts': dict(district_data),
            'blocks': dict(block_data),
            'users': dict(users_data),
        }

        activity_logger.info(
            'Prepared chart hierarchy | states=%d | districts=%d | blocks=%d | users=%d',
            len(states),
            len(districts),
            len(blocks),
            len(users)
        )

        return render_template(
            'dashboard/drill_chart.html',
            bar_chart_data=bar_chart_data
        )
    except Exception:
        error_logger.exception('Error while preparing dashboard charts data')
        raise

@blp.route('/states', methods=['GET','POST'])
def get_dashboard_states():
    access_logger.info(
        'Route accessed | action=get_dashboard_states | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    try:
        certificates = UserCourse.get_state_count()
        activity_logger.info('Fetched state metrics | count=%d', len(certificates))
        return jsonify(certificates)
    except Exception:
        error_logger.exception('Error fetching state metrics')
        return jsonify({'error': 'Failed to fetch states data'}), 500

@blp.route('/districts', methods=['POST'])
def get_dashboard_districts():
    access_logger.info(
        'Route accessed | action=get_dashboard_districts | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    data = json.loads(request.data)
    try:
        results = UserCourse.get_district_count(data['state_id'])
        activity_logger.info(
            'Fetched district metrics | state_id=%s | count=%d',
            data.get('state_id'),
            len(results)
        )
        return jsonify(results), 200
    except Exception:
        error_logger.exception('Error in get_districts | state_id=%s', data.get('state_id'))
        return jsonify({'error': 'Failed to fetch districts data'}), 500

@blp.route('/blocks', methods=['POST'])
def get_dashboard_blocks():
    access_logger.info(
        'Route accessed | action=get_dashboard_blocks | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    data = json.loads(request.data)
    try:
        results = UserCourse.get_block_count(data['state_id'], data['district_id'])
        activity_logger.info(
            'Fetched block metrics | state_id=%s | district_id=%s | count=%d',
            data.get('state_id'),
            data.get('district_id'),
            len(results)
        )
        return jsonify(results), 200
    except Exception:
        error_logger.exception(
            'Error in get_blocks | state_id=%s | district_id=%s',
            data.get('state_id'),
            data.get('district_id')
        )
        return jsonify({'error': 'Failed to fetch blocks data'}), 500



@blp.route('/activity_identification', methods=['GET'])
@login_required
def activity_identification():
    access_logger.info(
        'Route accessed | action=dashboard.activity_identification | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    # Dynamic dropdowns (ordered by id)
    clusters = orm_to_dict_list(Cluster.query.order_by(Cluster.id).all(), ["id", "name"])
    slopes = orm_to_dict_list(Slope.query.order_by(Slope.id).all(), ["id", "name"])
    ridges = orm_to_dict_list(Ridge.query.order_by(Ridge.id).all(), ["id", "name"])
    water_works = orm_to_dict_list(WaterWork.query.order_by(WaterWork.id).all(), ["id", "name"])
    nature_of_work = orm_to_dict_list(NatureOfWork.query.order_by(NatureOfWork.id).all(), ["id", "short_name"])
    location_specific = orm_to_dict_list(LocationSpecific.query.order_by(LocationSpecific.id).all(), ["id", "name"])

    categories = orm_to_dict_list(Category.query.order_by(Category.id).all(), ["id", "name"])
    beneficiaries = orm_to_dict_list(Beneficiary.query.order_by(Beneficiary.id).all(), ["id", "name"])
    activities_types = orm_to_dict_list(ActivityType.query.order_by(ActivityType.id).all(), ["id", "short_name"])
    major_scheduled_category = orm_to_dict_list(MajorScheduledCategory.query.order_by(MajorScheduledCategory.id).all(), ["id", "name"])
    work_types = orm_to_dict_list(WorkType.query.order_by(WorkType.id).all(), ["id", "name"])
    permissible_works = orm_to_dict_list(PermissibleWork.query.order_by(PermissibleWork.id).all(), ["id", "name"])

    activity_logger.info(
        'Rendering activity identification view | clusters=%d | categories=%d | permissible_works=%d | ip=%s',
        len(clusters),
        len(categories),
        len(permissible_works),
        _client_ip()
    )
    return render_template(
        "dashboard/activity_identification.html",
        page_subtitle="Identification Dashboard",
        page_title="Activity Identification",
        nature_of_work=nature_of_work,
        categories=categories,
        land_types=location_specific,
        work_types=work_types,
        clusters=clusters,
        ridges=ridges,
        beneficiaries=beneficiaries,
        activities=activities_types,
        slopes=slopes,
        water_works=water_works,
        major_scheduled_category=major_scheduled_category,
        permissible_works=permissible_works,
    )


