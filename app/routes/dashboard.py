from typing import List, Optional
from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import distinct
from app.models.dashboard import (
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

blp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def orm_to_dict_list(queryset, fields):
    """Convert ORM objects into list of dicts with only required fields."""
    return [{f: getattr(obj, f) for f in fields} for obj in queryset]

@blp.route('/activity_identification', methods=['GET'])
def activity_identification():
# 🔹 Dynamic dropdowns (ordered by id)
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


# Remove search handling from backend - simplified filter function
@blp.route('/activity_identification/filter', methods=['POST'])
def activity_identification_filter():
    """
    Dynamic filtering - NO search handling in backend
    """
    try:
        data = request.get_json() or {}
        # Remove search_term = data.get('search', '').strip().lower()

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
            "land_types": ActivityList.location_specifics,
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

        reorder_on_disable = {"location_specifics", "major_scheduled_category", "work_types", "permissible_works"}
        response_data = {}
        auto_fill_data = {}

        for key, (model, fields) in model_map.items():
            all_options = orm_to_dict_list(model.query.order_by(model.id).all(), fields)
            
            # NO search filtering here - removed the search logic
            
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

            # Check for auto-fill (including nature_of_works now)
            if enabled_count == 1 and not data.get(key):
                auto_fill_data[key] = {
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

        # Add auto_fill to response
        if auto_fill_data:
            response_data["auto_fill"] = auto_fill_data

        return jsonify({
            "success": True,
            "data": response_data
        })

    except Exception as e:
        print(f"Error in filtering: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500