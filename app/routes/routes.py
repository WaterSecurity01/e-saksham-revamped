import base64
import os
import shutil
from typing import OrderedDict
import uuid
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename 

from app.classes.SCORMparser import SCORMParser
from app.classes.forms import UploadForm
from app.classes.helper import get_lrs_query_string
from app.models import Course, User, UserCourse


blp = Blueprint("routes",__name__)

@blp.route("/")
@login_required
def index():
    return render_template('index.html')

@blp.route("/upload", methods=['GET','POST'])
@login_required
def upload():
    form = UploadForm()
    try:
        if request.method == 'POST':
            if 'scorm_file' not in request.files:
                return jsonify({'error': 'No file selected'}), 400
            
            file = request.files['scorm_file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if file and file.filename.endswith('.zip'):
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                if not os.path.exists(file_path):
                    file.save(file_path)
                
                # Generate unique package ID
                package_id = str(uuid.uuid4())
                extract_path = os.path.join(current_app.config['SCORM_FOLDER'], package_id)
                title = request.form.get('course_title')
                description = request.form.get('description')
                
                # Parse SCORM package
                parser = SCORMParser(file_path, extract_path, package_id, title, description)
                if parser.extract_package():
                    # Save course to database
                    course = Course(
                        name=parser.title,
                        description=parser.description,
                        scorm_version=parser.scorm_version,
                        package_path=parser.package_path,
                        manifest_path=parser.manifest_path,
                        manifest_identifier=parser.manifest_identifier,
                        manifest_title=parser.manifest_title,
                        package_id=parser.package_id,
                        launch_url=parser.launch_url)
                    if parser.duplicate_package_path:
                        course.update()
                        shutil.rmtree(parser.duplicate_package_path)
                    else:
                        course.save()
                    
                    # Clean up uploaded zip file
                    os.remove(file_path)
                    flash(message="SCORM package uploaded successfully",category="success" )
                    return redirect(url_for('routes.courses'))
                    # return jsonify({'success': True, 'course_id': course_id, 'message': 'SCORM package uploaded successfully'})
                else:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    shutil.rmtree(extract_path,ignore_errors=True)
                    flash(message= f'SCORM package with manifest ID already exists',category="error" )
                    # return jsonify({'error': 'Invalid SCORM package'}), 400
            else:
                flash(message= f'Please upload a ZIP file',category="error" )
                # return jsonify({'error': 'Please upload a ZIP file'}), 400
    except Exception as ex:
        if os.path.isfile(file_path):
            os.remove(file_path)
        shutil.rmtree(extract_path, ignore_errors=True)
        flash(message= f'There was an error while uploading {ex}',category="error" )
        # return redirect(url_for('routes.upload'))
        # return jsonify({'error': f'There was an error while uploading {ex}'}), 400
    return render_template('/lms/upload.html', form=form)

@blp.route('/courses')
@login_required
def courses():
    courses = Course.find_all()
    user = User.get_user_by_id(current_user.id)
    return render_template('lms/courses.html', courses=courses, user=user)

@blp.route('/course/<int:course_id>')
@login_required
def launch(course_id):
    course = Course.find_by_id(course_id)
    user = current_user
    return render_template('lms/launch.html', course=course, user=user)

@blp.route('/launch/<int:course_id>')
@login_required
def launch_course(course_id):
    user = User.get_user_by_id(current_user.id)
    course = Course.find_by_id(course_id)
    base_url = request.url_root.rstrip('/')
    if not UserCourse.find_by_user_and_course_id(user.id,course.id):
        user_course = UserCourse(user_id=user.id, course_id=course.id, certificate_issued=False)
        user_course.save()
    # actor = {
    #     "mbox": user.email,
    #     "objectType": "Agent",
    #     "name": user.name
    #     }
    # endpoint = '/api/lrs'
    # auth = get_basic_auth(key=user.name,secret_key=user.email)
    query_string = get_lrs_query_string(user,base_url)
    # slxapi=%7B%22actor%22%3A%7B%22mbox%22%3A%22mailto%3Aanonymous%40anonymous.com%22%2C%22objectType%22%3A%22Agent%22%2C%22name%22%3A%22anonymous%22%7D%2C%22endpoint%22%3A%22http%3A%2F%2F127.0.0.1%3A5000{{%2Flrs%2Fxapi}}%22%2C%22auth%22%3A%22{{Basic%20dzI0SnlUbjBTSUVIZlM6VnJRczdmRXVYVnJkQWhOMUVJSDF4cVZDaE1XSjdvQmd4ajM4SjNpMnl3WQ}}%3D%3D%22%7D
    # query_string = 'slxapi=%7B%22actor%22%3A%7B%22mbox%22%3A%22mailto%3Aamar.saxena%40gmail.co%22%2C%22objectType%22%3A%22Agent%22%2C%22name%22%3A%22Amar%20Saxena%22%7D%2C%22endpoint%22%3A%22%2Flrs%2Fapi%22%2C%22auth%22%3A%22Basic%20cHVibGljX2tleTpzZWNyZXRfa2V5%22%7D'
            
    return render_template('lms/player.html', course=course, course_id = course.id, query_string=query_string)

@blp.route('/scorm/<int:course_id>/<path:filename>')
@login_required
def serve_scorm_content(course_id, filename):
    course = Course.find_by_id(course_id=course_id)
    
    if not course:
        return "Course not found", 404
    # filename = filename + "?resume=8"
    package_path = course.package_path
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    abs_package_path = os.path.join(BASE_DIR.split("/routes")[0], package_path.split("app/")[1])
    
    return send_from_directory(abs_package_path, filename)



