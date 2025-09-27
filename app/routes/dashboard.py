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


def _build_enriched_options(model, fields, enabled_ids):
    """Return ordered option dictionaries including disabled flags for search results."""
    fetch_fields = set(fields) | {"id"}
    options = []

    for obj in model.query.order_by(model.id).all():
        option = {field: getattr(obj, field) for field in fetch_fields}
        option["disabled"] = obj.id not in enabled_ids
        options.append(option)

    options.sort(key=lambda record: (record["disabled"], record["id"]))
    return options

@blp.route('/activity_identification', methods=['GET'])
def activity_identification():
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


@blp.route('/activity_identification/search', methods=['POST'])
def activity_identification_search():
    """Search permissible works and surface related options for quick filtering."""
    try:
        data = request.get_json() or {}
        search_term = data.get('search', '').strip().lower()

        if not search_term or len(search_term) < 3:
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

        return jsonify({
            "success": True,
            "data": response_payload
        })

    except Exception as exc:
        print(f"Error in search: {exc}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


@blp.route('/activity_identification/filter', methods=['POST'])
def activity_identification_filter():
    """
    Enhanced filtering with checkbox support and auto-selection logic
    """
    try:
        data = request.get_json() or {}

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
