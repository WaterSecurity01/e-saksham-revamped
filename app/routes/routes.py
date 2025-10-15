import base64
import csv
from datetime import datetime
from io import StringIO
import os
import re
from flask import Blueprint, Response, current_app, flash, json, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_login import current_user, login_required
from app.db import db
from app.classes.forms import ProfileForm, FeedbackForm
from app.classes.helper import generate_math_captcha, get_lrs_query_string
from app.classes.logging import get_route_loggers, _client_ip
from app.models import Course, User, UserCourse
from app.models.block import Block
from app.models.district import District
from app.models.feedback import Feedback
from app.models.state_ut import State_UT
from app.models.videos import Video


blp = Blueprint("routes",__name__)

_loggers = get_route_loggers('routes')
access_logger = _loggers.access
error_logger = _loggers.error
activity_logger = _loggers.activity


@blp.route("/")
def index():
    access_logger.info(
        'Route accessed | action=routes.index | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    return render_template('index.html')

@blp.route("/contact")

def contact():
    access_logger.info(
        'Route accessed | action=routes.contact | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    return render_template('other/contact.html')

@blp.route("/feedback", methods=['GET','POST'])
@login_required
def feedback():
    access_logger.info(
        'Route accessed | action=routes.feedback | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    form = FeedbackForm()
    if request.method == "POST":
        name = current_user.name
        email = current_user.email
        subject = request.form.get('subject', '').strip()
        message_category = request.form.get('message_type', '').strip()
        rating = request.form.get('rating') or request.form.get('rating-mobile')
        captcha_response = request.form.get('captcha_answer','').strip()
        message = request.form.get('message', '').strip()

        if not subject or not (1 <= len(subject) <= 100):
            activity_logger.warning('Feedback validation failed | reason=subject | user=%s | ip=%s', email, _client_ip())
            flash("Subject is required (max 100 characters).")
            return redirect(url_for('routes.feedback'))
        allowed_categories = {'course', 'technical', 'subject_related', 'admin', 'others'}
        if not message_category or message_category not in allowed_categories:
            activity_logger.warning('Feedback validation failed | reason=category | user=%s | ip=%s', email, _client_ip())
            flash("Invalid message category.","error")
            return redirect(url_for('routes.feedback'))
        if rating:
            try:
                int_rating = int(rating)
                if int_rating < 1 or int_rating > 5:
                    raise ValueError
            except Exception:
                activity_logger.warning('Feedback validation failed | reason=rating | user=%s | ip=%s', email, _client_ip())
                flash("Rating must be a number between 1 and 5.","error")
                return redirect(url_for('routes.feedback'))
        if not captcha_response:
            activity_logger.warning('Feedback validation failed | reason=captcha_missing | user=%s | ip=%s', email, _client_ip())
            flash('Please fill the captcha.')
            return redirect(url_for('routes.feedback'))
        
        captcha_answer = int(session.get('captcha_answer'))
        captcha_response = int(captcha_response)
        verification_response = captcha_answer == captcha_response
        if not verification_response:
            activity_logger.warning('Feedback captcha failed | user=%s | ip=%s', email, _client_ip())
            flash('CAPTCHA verification failed. Please try again.', "error")
            return redirect(url_for('routes.feedback'))
        
        try:
            feedback = Feedback(
                name=name,
                email=email,
                subject=subject,
                message_category=message_category,
                message=message,
                rating=int_rating if rating else 0
            )
            feedback.save_to_db()
            activity_logger.info('Feedback submitted | user=%s | category=%s | ip=%s', email, message_category, _client_ip())
            flash("Thank you for sharing your feedback.", "success")
        except Exception as ex:
            error_logger.exception('Error saving feedback | user=%s', email)
            flash("There was an error submitting your feedback. Please try again later.", "error")
        return redirect(url_for('routes.feedback'))

    captcha_question = generate_math_captcha()
    return render_template('other/feedback.html', form = form, captcha_question = captcha_question)


@blp.route('/faq')
def faq():
    access_logger.info(
        'Route accessed | action=routes.faq | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    return render_template('other/faq.html')

@blp.route('/pdf/<string:pdf_name>')
@login_required
def view_pdf(pdf_name):
    access_logger.info(
        'Route accessed | action=routes.view_pdf | method=%s | path=%s | ip=%s | pdf=%s',
        request.method,
        request.path,
        _client_ip(),
        pdf_name
    )
    filename = f"{pdf_name}.pdf"
    pdf_title = ""
    if pdf_name == 'training_manual':
        pdf_title = 'Yuktdhara Manual'
    else:
        pdf_title = 'Yuktdhara Leaflet'
    activity_logger.info('PDF viewed | user_id=%s | pdf=%s', current_user.id, pdf_name)
    return render_template('other/pdf_viewer.html', filename=filename, pdf_title=pdf_title)


@blp.route('/view/<string:filename>')
@login_required
def render_pdf(filename):
    access_logger.info(
        'Route accessed | action=routes.render_pdf | method=%s | path=%s | ip=%s | filename=%s',
        request.method,
        request.path,
        _client_ip(),
        filename
    )
    file_path = "/app/static/pdfs"
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    abs_package_path = os.path.join(BASE_DIR.split("/app")[0], file_path)
    
    activity_logger.info('Static PDF served | user_id=%s | filename=%s', current_user.id, filename)
    return send_from_directory(abs_package_path, filename)

########## LMS related #######


@blp.route('/courses')
@login_required
def courses():
    access_logger.info(
        'Route accessed | action=routes.courses | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    courses = Course.find_all()
    user = User.get_user_by_id(current_user.id)
    activity_logger.info('Courses page viewed | user_id=%s | course_count=%d', current_user.id, len(courses))
    return render_template('lms/courses.html', courses=courses, user=user)

@blp.route('/course/<int:course_id>')
@login_required
def launch(course_id):
    access_logger.info(
        'Route accessed | action=routes.course_detail | method=%s | path=%s | ip=%s | user_id=%s | course_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id,
        course_id
    )
    course = Course.find_by_id(course_id)
    user = current_user
    activity_logger.info('Course detail viewed | user_id=%s | course_id=%s', current_user.id, course_id)
    return render_template('lms/launch.html', course=course, user=user)

@blp.route('/launch/<int:course_id>')
@login_required
def launch_course(course_id):
    access_logger.info(
        'Route accessed | action=routes.launch_course | method=%s | path=%s | ip=%s | user_id=%s | course_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id,
        course_id
    )
    user = User.get_user_by_id(current_user.id)
    course = Course.find_by_id(course_id)
    base_url = request.url_root.rstrip('/')
    if not UserCourse.find_by_user_and_course_id(user.id,course.id):
        user_course = UserCourse(user_id=user.id, course_id=course.id, certificate_issued=False)
        user_course.save()
        activity_logger.info('User enrolled in course | user_id=%s | course_id=%s', user.id, course.id)
    query_string = get_lrs_query_string(user, base_url)
           
    activity_logger.info('Course launched | user_id=%s | course_id=%s', user.id, course.id)
    return render_template('lms/player.html', course=course, course_id = course.id, query_string=query_string)

@blp.route('/scorm/<int:course_id>/<path:filename>')
@login_required
def serve_scorm_content(course_id, filename):
    access_logger.info(
        'Route accessed | action=routes.serve_scorm | method=%s | path=%s | ip=%s | user_id=%s | course_id=%s | filename=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id,
        course_id,
        filename
    )
    course = Course.find_by_id(course_id=course_id)
    
    if not course:
        activity_logger.warning('SCORM asset request for missing course | user_id=%s | course_id=%s', current_user.id, course_id)
        return "Course not found", 404
    # filename = filename + "?resume=8"
    package_path = course.package_path
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    abs_package_path = os.path.join(BASE_DIR.split("/routes")[0], package_path.split("app/")[1])
    
    activity_logger.info('SCORM asset served | user_id=%s | course_id=%s | filename=%s', current_user.id, course_id, filename)
    return send_from_directory(abs_package_path, filename)

@blp.route('/users_search')
@login_required
def users_search():
    access_logger.info(
        'Route accessed | action=routes.users_search | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    courses = Course.get_all_courses()
    activity_logger.info('Rendered users search page | user_id=%s | course_count=%d', current_user.id, len(courses))
    return render_template('other/users_search.html', courses=courses)

@blp.route('/verifiy_certificate/<string:uuid>/<int:course_id>')
def verifiy_certificate(uuid, course_id):
    # Logic to verify the certificate using the UUID
    access_logger.info(
        'Route accessed | action=routes.verify_certificate | method=%s | path=%s | ip=%s | uuid=%s',
        request.method,
        request.path,
        _client_ip(),
        uuid
    )
    user = User.get_user_by_uuid(uuid)
    if user:
        certificate_details = UserCourse.get_certificate_details(user.id,course_id)
        if certificate_details:
            activity_logger.info('Certificate verified | uuid=%s | user_id=%s', uuid, user.id)
            return render_template('other/verify_certificate.html', certificate=certificate_details, user=user)
        else:
            activity_logger.warning('Certificate verification failed - no certificate | uuid=%s | user_id=%s', uuid, user.id)
            return render_template('other/verify_certificate.html', error="No certificate found for this user.")
    else:
        activity_logger.warning('Certificate verification failed - invalid uuid | uuid=%s', uuid)
        return render_template('other/verify_certificate.html', error="Invalid certificate UUID.")


@blp.route('/video_gallery')
@login_required
def video_gallery():
    raw_videos = Video.get_all()
    video_list = [
        {
            "title": video['title'],
            "duration": video['length'],
            "embedUrl": video['embed_url'],
            "is_short": video.get('is_short', False),
            "is_how_to": video.get('is_how_to', True)
        }
        for video in raw_videos
        if video.get('embed_url')
    ]
    access_logger.info(
        'Route accessed | action=routes.video_gallery | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    activity_logger.info('Video gallery rendered | user_id=%s | videos=%d', current_user.id, len(video_list))
    return render_template('other/video_gallery.html',videos=video_list)   
