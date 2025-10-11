from collections import deque
import csv
import datetime
from io import StringIO
import os
import shutil
import uuid
from werkzeug.utils import secure_filename 

from flask import Blueprint, Response, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.classes.SCORMparser import SCORMParser
from app.classes.forms import RoleForm, UploadForm, menuItemForm
from app.classes.helper import (
    convert_to_embed_url,
    extract_youtube_video_id,
    generate_math_captcha,
    is_youtube_shorts_url,
    validate_youtube_embed_url,admin_required
)
from app.classes.logging import LOG_ROOT, get_route_loggers, _client_ip
from app.models.courses import Course
from app.models.feedback import Feedback
from app.models.menu_in_role import MenuInRole
from app.models.menu_item import MenuItem
from app.models.role import Role
from app.models.user import User
from app.models.user_courses import UserCourse
from app.models.user_in_role import UserInRole
from passlib.hash import pbkdf2_sha256

from app.models.videos import Video



blp = Blueprint('admin',__name__,url_prefix='/admin')

_loggers = get_route_loggers('admin')
access_logger = _loggers.access
error_logger = _loggers.error
activity_logger = _loggers.activity


@blp.route('/roles',methods=['GET','POST'])
@login_required
@admin_required
def roles():
    access_logger.info(
        'Route accessed | action=admin.roles | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    form = RoleForm()
    try:
        if form.validate_on_submit():
            role = Role.get_role_by_name(form.name.data)
            if not role:
                new_role = Role(name=form.name.data, description=form.description.data)
                new_role.save()
                activity_logger.info('Role created | name=%s | ip=%s', form.name.data, _client_ip())
                flash("Role added successfully!", "success")
                return redirect(url_for("admin.roles"))
            flash("Role already exists!", "success")

        all_roles = Role.query.all()
        activity_logger.info('Roles listing rendered | count=%d | ip=%s', len(all_roles), _client_ip())
        return render_template("admin/roles.html", roles=all_roles, form=form)
    except Exception:
        error_logger.exception('Error handling admin.roles request')
        flash("Unable to process role request at the moment.", "error")
        return redirect(url_for("admin.roles"))

@blp.route('/menu_items',methods=['GET','POST'])
@login_required
@admin_required
def menu_items():
    access_logger.info(
        'Route accessed | action=admin.menu_items | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    form = menuItemForm()
    all_menu_items = MenuItem.query.all()
    form.parent_id.choices = [(-1, "Select Parent"), (0, "Root Node")]
    form.parent_id.choices += [(item.id, item.name) for item in all_menu_items]
    try:
        if form.validate_on_submit():
            menuItem = MenuItem.get_menuItem_by_name(form.name.data)
            if not menuItem:
                new_menuItem = MenuItem(form.name.data,form.url.data,form.icon.data,form.parent_id.data,form.order_index.data)
                new_menuItem.save()
                activity_logger.info('Menu item created | name=%s | ip=%s', form.name.data, _client_ip())
                flash("Menu item added successfully!", "success")
                return redirect(url_for("admin.menu_items"))
            flash("Menu item already exists!", "success")

        activity_logger.info('Menu items listing rendered | count=%d | ip=%s', len(all_menu_items), _client_ip())
        return render_template("admin/menu_items.html", menu_items=all_menu_items, form=form)
    except Exception:
        error_logger.exception('Error handling admin.menu_items request')
        flash("Unable to process menu item request at the moment.", "error")
        return redirect(url_for("admin.menu_items"))

@blp.route('/users_in_roles', methods=['GET','POST'])
@login_required
@admin_required
def users_in_roles():
    access_logger.info(
        'Route accessed | action=admin.users_in_roles | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    if request.method == 'POST':
        activity_logger.info('Users in roles POST request received | ip=%s', _client_ip())
    try:
        roles = Role.get_all()
        user_in_roles = UserInRole.get_all()
        for i in range(10):
            user_in_roles.append({"serial": i + 1,"user_id": i,"username": "username_" + str(i),"roles": ["user"]})
        activity_logger.info('Users in roles view rendered | roles=%d | users=%d | ip=%s', len(roles), len(user_in_roles), _client_ip())
        return render_template('admin/users_in_roles.html', roles = roles, users=user_in_roles)
    except Exception:
        error_logger.exception('Error loading users in roles data')
        flash('Unable to load users in roles data.', 'error')
        return redirect(url_for('admin.roles'))

@blp.route("/menu_in_roles")
@login_required
@admin_required
def menu_in_roles():
    access_logger.info(
        'Route accessed | action=admin.menu_in_roles | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    try:
        roles = Role.get_all()
        menu_in_roles = MenuInRole.get_all()
        activity_logger.info('Menu-in-roles view rendered | roles=%d | mappings=%d | ip=%s', len(roles), len(menu_in_roles), _client_ip())
        return render_template('admin/menu_in_roles.html', roles = roles, menu_items = menu_in_roles)
    except Exception:
        error_logger.exception('Error loading menu in roles data')
        flash('Unable to load menu role mappings.', 'error')
        return redirect(url_for('admin.roles'))


@blp.route('/logs')
@login_required
@admin_required
def view_logs():
    access_logger.info(
        'Route accessed | action=admin.view_logs | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )

    try:
        available_modules = sorted([path.name for path in LOG_ROOT.iterdir() if path.is_dir()])
    except OSError:
        available_modules = []

    log_categories = ('access', 'error', 'activity')

    selected_module = (request.args.get('module') or '').lower()
    if selected_module not in available_modules:
        selected_module = available_modules[0] if available_modules else None

    selected_category = (request.args.get('category') or 'access').lower()
    if selected_category not in log_categories:
        selected_category = 'access'

    log_entries = []
    log_file_name = None
    log_error = None

    if selected_module:
        log_file = LOG_ROOT / selected_module / f'{selected_module}_{selected_category}.log'
        log_file_name = log_file.name
        if log_file.exists():
            try:
                with log_file.open('r', encoding='utf-8', errors='replace') as handle:
                    for raw_line in deque(handle, maxlen=250):
                        stripped = raw_line.rstrip('\n')
                        timestamp = ''
                        message = stripped
                        if '|' in stripped:
                            parts = stripped.split('|', 1)
                            timestamp = parts[0].strip()
                            message = parts[1].strip()
                        log_entries.append({'timestamp': timestamp, 'message': message})
            except OSError:
                log_error = f'Unable to read {selected_category} log for {selected_module}.'
        else:
            log_error = f'No {selected_category} log available for {selected_module}.'
    else:
        log_error = 'No log modules found.'

    return render_template(
        'admin/logs.html',
        modules=available_modules,
        categories=log_categories,
        selected_module=selected_module,
        selected_category=selected_category,
        log_entries=log_entries,
        log_file_name=log_file_name,
        log_error=log_error
    )


@blp.route('/user_management')
@login_required
@admin_required
def user_management():
    # Just render the HTML, JS will fetch users via API
    access_logger.info(
        'Route accessed | action=admin.user_management | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    return render_template('admin/user_management.html')


@blp.route('/export_users')
@login_required
@admin_required
def export_users():
    access_logger.info(
        'Route accessed | action=admin.export_users | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    try:
        csv_data = StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow([
            'UUID', 'Name', 'Email', 'Status', 'Admin', 'Registration Date'
        ])
        users = User.query.all()
        for user in users:
            csv_writer.writerow([
                user.uuid,
                user.name,
                user.email,
                'Active' if user.is_active else 'Inactive',
                'Yes' if user.is_admin else 'No',
                user.registered_on.strftime('%Y-%m-%d %H:%M:%S')
            ])
        response = Response(
            csv_data.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=users_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
        activity_logger.info(f"Exported users data ({len(users)} users)")
        return response
    except Exception as e:
        error_logger.error(f"Error exporting users: {e}")
        flash(f'Error exporting users')
        return redirect(url_for('admin.user_management'))

@blp.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    access_logger.info(
        'Route accessed | action=admin.add_user | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = str.upper(email[0])+email[1:4]+'_123@'
        is_active = 'is_active' in request.form
        is_admin = 'is_admin' in request.form

        if not name or not email or not password:
            flash('Name, email and password are required')
            return redirect(url_for('admin.add_user'))
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('A user with this email already exists')
            return redirect(url_for('admin.add_user'))
        try:
            new_user = User(
                name=name,
                email=email,
                password=pbkdf2_sha256.hash(password),
                is_active=is_active,
                is_admin=is_admin
            )
            db.session.add(new_user)
            db.session.commit()
            user_id=current_user.id,
            action=f"Created new user: {name} ({email})"
            activity_logger.info(f"Added new user: {email}")
            flash(f'User {name} created successfully')
            return redirect(url_for('admin.user_management'))
        except Exception as e:
            db.session.rollback()
            error_logger.error(f"Error creating user {email}: {e}")
            flash(f'Error creating user')
            return redirect(url_for('admin.add_user'))
    return render_template('admin/add_user.html')

@blp.route('/update_certificate', methods=['GET','POST'])
@login_required
@admin_required
def update_certificate():
    access_logger.info(
        'Route accessed | action=admin.update_certificate | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    captcha_question = generate_math_captcha()
    courses = Course.get_all_courses()
    if "@esaksham.nic.in" in current_user.email:
        return render_template(
            "admin/cert_update.html",
            captcha_question=captcha_question,
            developer=True,
            courses=courses
        )

    user = User.get_user_by_id(current_user.id)
    if not user or not user.get('state_id'):
        flash("Please update your profile with state/district/block", "danger")
    return render_template(
        "admin/cert_update.html",
        captcha_question=captcha_question,
        developer=False,
        courses=courses
    )

@blp.route("/upload_course", methods=['GET','POST'])
@login_required
@admin_required
def upload_course():
    access_logger.info(
        'Route accessed | action=admin.upload_course | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    form = UploadForm()
    file_path = None
    extract_path = None
    try:
        if request.method == 'POST':
            activity_logger.info('SCORM upload attempt | user_id=%s | ip=%s', current_user.id, _client_ip())
            if 'scorm_file' not in request.files:
                activity_logger.warning('SCORM upload failed | reason=file_missing | user_id=%s | ip=%s', current_user.id, _client_ip())
                return jsonify({'error': 'No file selected'}), 400
            
            file = request.files['scorm_file']
            if file.filename == '':
                activity_logger.warning('SCORM upload failed | reason=filename_missing | user_id=%s | ip=%s', current_user.id, _client_ip())
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
                short_name = request.form.get('short_name')
                topics = request.form.get('topics','').strip()
                
                # Parse SCORM package
                parser = SCORMParser(file_path, extract_path, package_id, title, description)
                if parser.extract_package():
                    # Save course to database
                    course = Course(
                        name=parser.title,
                        short_name=short_name,
                        description=parser.description,
                        scorm_version=parser.scorm_version,
                        package_path=parser.package_path,
                        manifest_path=parser.manifest_path,
                        manifest_identifier=parser.manifest_identifier,
                        manifest_title=parser.manifest_title,
                        package_id=parser.package_id,
                        topics=topics,
                        launch_url=parser.launch_url)
                    if parser.duplicate_package_path:
                        course.update()
                        shutil.rmtree(parser.duplicate_package_path)
                    else:
                        course.save()
                    
                    # Clean up uploaded zip file
                    os.remove(file_path)
                    activity_logger.info('SCORM upload successful | user_id=%s | package_id=%s', current_user.id, parser.package_id)
                    flash(message="SCORM package uploaded successfully",category="success" )
                    return redirect(url_for('routes.courses'))
                    # return jsonify({'success': True, 'course_id': course_id, 'message': 'SCORM package uploaded successfully'})
                else:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    shutil.rmtree(extract_path,ignore_errors=True)
                    activity_logger.warning('SCORM upload failed | reason=duplicate_manifest | user_id=%s | package_id=%s', current_user.id, getattr(parser, 'package_id', 'unknown'))
                    flash(message= f'SCORM package with manifest ID already exists',category="error" )
                    # return jsonify({'error': 'Invalid SCORM package'}), 400
            else:
                flash(message= f'Please upload a ZIP file',category="error" )
                # return jsonify({'error': 'Please upload a ZIP file'}), 400
    except Exception as ex:
        error_logger.exception('Error during SCORM upload | user_id=%s', current_user.id)
        if file_path and os.path.isfile(file_path):
            os.remove(file_path)
        if extract_path:
            shutil.rmtree(extract_path, ignore_errors=True)
        flash(message= f'There was an error while uploading {ex}',category="error" )
        # return redirect(url_for('admin.upload_course'))
        # return jsonify({'error': f'There was an error while uploading {ex}'}), 400
    return render_template('/lms/upload.html', form=form)


@blp.route('/upload_videos', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_videos():
    """
    Handle video upload form
    GET: Display the upload form
    POST: Process form submission and save video to database
    """
    access_logger.info(
        'Route accessed | action=admin.upload_videos | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    
    form_data = {
        'title': request.form.get('title', '').strip(),
        'length': request.form.get('length', '').strip(),
        'video_url': request.form.get('video_url', '').strip(),
        'embed_url': request.form.get('embed_url', '').strip(),
        'is_short': request.form.get('is_short'),
        'video_category': request.form.get('video_category', 'how_to')
    }

    def render_form(message=None, category='error'):
        if message:
            flash(message, category)
        return render_template('admin/upload_videos.html', form_data=form_data)

    if request.method == 'GET':
        return render_template('admin/upload_videos.html', form_data={})

    try:
        title = form_data['title']
        length = form_data['length']
        video_url = form_data['video_url']
        embed_url = form_data['embed_url']
        is_short = form_data['is_short'] == 'true'
        video_category = form_data['video_category']
        is_how_to = video_category != 'workshop'

        if not title:
            return render_form('Video title is required.')
        if not length:
            return render_form('Video length is required.')
        if not video_url and not embed_url:
            return render_form('YouTube URL is required.')
        if len(title) > 128:
            return render_form('Video title must be 128 characters or less.')
        if len(length) > 128:
            return render_form('Video length must be 128 characters or less.')

        if video_url and not embed_url:
            embed_url = convert_to_embed_url(video_url)
            if not embed_url:
                return render_form('Could not convert the provided YouTube URL to embed format.')
            form_data['embed_url'] = embed_url

        if len(embed_url) > 256:
            return render_form('Embed URL must be 256 characters or less.')
        if not validate_youtube_embed_url(embed_url):
            return render_form('Please enter a valid YouTube URL.')

        video_id = extract_youtube_video_id(embed_url)
        if not video_id:
            return render_form('Could not extract video ID from the provided URL.')

        existing_video = Video.query.filter_by(embed_url=embed_url).first()
        if existing_video:
            return render_form('A video with this embed URL already exists.')

        if video_url and is_youtube_shorts_url(video_url):
            is_short = True

        new_video = Video(
            title=title,
            length=length,
            embed_url=embed_url,
            is_short=is_short,
            is_how_to=is_how_to
        )

        db.session.add(new_video)
        db.session.commit()

        flash(f'Video "{title}" has been successfully uploaded!', 'success')
        return redirect(url_for('routes.videos_gallery'))

    except Exception as e:
        db.session.rollback()
        return render_form(f'An error occurred while uploading the video: {str(e)}')

@blp.route("/view_feedback")
@login_required
@admin_required
def view_feedback():
    access_logger.info(
        'Route accessed | action=admin.view_feedback | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    feedbacks = [] 
    for feedback in Feedback.query.order_by(Feedback.created_at.desc()).all():
        feedbacks.append({
            'id': feedback.id,
            'name':feedback.name,
            'email':feedback.email,
            'subject':feedback.subject,
            'category':feedback.message_category,
            'message':feedback.message,
            'rating':feedback.rating,
            'created_at':feedback.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    activity_logger.info('Feedback list viewed | count=%d | ip=%s', len(feedbacks), _client_ip())
    return render_template('admin/view_feedback.html', feedbacks = feedbacks)

@blp.route('/export-feedback')
@login_required
@admin_required
def export_feedback():
    access_logger.info(
        'Route accessed | action=admin.export_feedback | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    try:
        csv_data = StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow([
            'ID', 'Name', 'Email', 'Subject', 'Category', 'Message', 'Rating',
            'Has Image', 'Date Created'
        ])
        feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
        for feedback in feedbacks:
            csv_writer.writerow([
                feedback.id,
                feedback.name,
                feedback.email,
                feedback.subject,
                feedback.message_category,
                feedback.message,
                feedback.rating,
                'Yes' if feedback.image_filename else 'No',
                feedback.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        activity_logger.info('Exported feedback data | user_id=%s | count=%d', current_user.id, len(feedbacks))
        response = Response(
            csv_data.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=feedback_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
        return response
    except Exception:
        error_logger.exception('Error exporting feedback CSV | user_id=%s', current_user.id)
        flash('Error exporting feedback')
        return redirect(url_for('admin.view_feedback'))
