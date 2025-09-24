from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, jsonify, request, session
from flask_login import current_user

from app.db import db
from app.models import ScormData


blp = Blueprint('api_lms',__name__, url_prefix='/api/lms')

# SCORM API endpoints - Revised
from flask import jsonify, request, session

@blp.route('/scorm/<int:course_id>/initialize', methods=['POST'])
def scorm_initialize(course_id):
    """Initialize SCORM session - should return true/false, not suspend_data"""
    try:
        # Check if user has existing progress
        user_id = current_user.id
        if not user_id:
            return jsonify({'result': 'false', 'errorCode': '101'})  # No current user session
        
        # Initialize session state
        session[f'scorm_{course_id}_initialized'] = True
        
        return jsonify({'result': 'true', 'errorCode': '0'})
    except Exception as e:
        return jsonify({'result': 'false', 'errorCode': '101'})
    

# flask backend:
@blp.route('/scorm/<int:course_id>/get_value', methods=['POST'])
def scorm_get_value(course_id):
    """Get SCORM data value"""
    try:
        data = request.get_json()
        cmi_key = data.get('element', '')
        user_id = current_user.id
        print(cmi_key)
        result = ScormData.get_by_key(user_id, course_id, cmi_key)
        if result: 
            print(result.cmi_value)
            return jsonify({'result': result.cmi_value, 'errorCode': '0'})
        else:
            print('passed')
            return jsonify({'result': '', 'errorCode': '101'})

    except Exception as e:
        print("Error in scorm_get_value:", str(e))
        return jsonify({'result': '', 'errorCode': '101'})


@blp.route('/scorm/<int:course_id>/set_value', methods=['POST'])
def scorm_set_value(course_id):
    """Set SCORM data value"""
    try:
        data = request.get_json()
        print("set_value:")
        print(data)
        cmi_key = data.get('element', '')
        cmi_value = data.get('value', '')
        user_id = current_user.id
        
        if not session.get(f'scorm_{course_id}_initialized'):
            return jsonify({'result': 'false', 'errorCode': '132'})  # Not initialized
        
        # Validate required elements
        if not cmi_key:
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
        return jsonify({'result': 'true', 'errorCode': '0'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'result': 'false', 'errorCode': '101'})

@blp.route('/scorm/<int:course_id>/commit', methods=['POST'])
def scorm_commit(course_id):
    """Commit SCORM data to persistent storage"""
    try:
        if not session.get(f'scorm_{course_id}_initialized'):
            return jsonify({'result': 'false', 'errorCode': '132'})  # Not initialized
        
        # Force commit any pending database changes
        db.session.commit()
        return jsonify({'result': 'true', 'errorCode': '0'})
        
    except Exception as e:
        return jsonify({'result': 'false', 'errorCode': '101'})

@blp.route('/scorm/<int:course_id>/finish', methods=['POST'])
def scorm_finish(course_id):
    """Finish SCORM session"""
    try:
        if not session.get(f'scorm_{course_id}_initialized'):
            return jsonify({'result': 'false', 'errorCode': '132'})  # Not initialized
        
        # Commit any final data
        db.session.commit()
        
        # Clear session state
        session.pop(f'scorm_{course_id}_initialized', None)
        
        return jsonify({'result': 'true', 'errorCode': '0'})
        
    except Exception as e:
        return jsonify({'result': 'false', 'errorCode': '101'})

@blp.route('/scorm/<int:course_id>/get_last_error', methods=['POST'])
def scorm_get_last_error(course_id):
    """Get last error code"""
    return jsonify({'result': '0', 'errorCode': '0'})

@blp.route('/scorm/<int:course_id>/get_error_string', methods=['POST'])
def scorm_get_error_string(course_id):
    """Get error string for error code"""
    data = request.get_json()
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
    return jsonify({'result': '', 'errorCode': '0'})
