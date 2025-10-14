import datetime
import re
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user,login_manager, logout_user
from app.classes.forms import ChangePasswordForm, LoginForm, ProfileForm, RegisterForm
from app.classes.helper import decrypt_password, generate_math_captcha
from app.classes.logging import get_route_loggers, _client_ip
from app import db
from app.models import User
from app.models.block import Block
from app.models.courses import Course
from app.models.district import District
from app.models.state_ut import State_UT
from app.models.user_courses import UserCourse
from passlib.hash import pbkdf2_sha256

from app.models.user_in_role import UserInRole


blp = Blueprint('auth', __name__, url_prefix='/auth')

_loggers = get_route_loggers('auth')
access_logger = _loggers.access
error_logger = _loggers.error
activity_logger = _loggers.activity


@blp.route('/login', methods=['GET','POST'])
def login():
    access_logger.info(
        'Route accessed | action=auth.login | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    # Already logged in → redirect
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.username.data.strip().lower()
        activity_logger.info('Login attempt | email=%s | ip=%s', email, _client_ip())
        try:
            password = decrypt_password(form.password.data or "")
            captcha_response = request.form.get('captcha_answer','').strip()
            expected_captcha = session.get('captcha_answer')
            if not expected_captcha or captcha_response != expected_captcha:
                activity_logger.warning('Login captcha failed | email=%s | ip=%s', email, _client_ip())
                flash("Invalid CAPTCHA answer. Please try again.", "danger")
                captcha_question = generate_math_captcha()
                return render_template('auth/login.html', form=form, captcha_question=captcha_question)

            user = User.get_user_by_email(email)

            if user and pbkdf2_sha256.verify(password, user.password):
                login_user(user, remember=form.remember_me.data)
                session.pop('captcha_answer', None)  # clear captcha on success
                activity_logger.info('Login success | user_id=%s | ip=%s', user.id, _client_ip())

                next_page = request.args.get('next')
                return redirect(next_page or url_for('routes.index'))

            activity_logger.warning('Login failed | reason=invalid_credentials | email=%s | ip=%s', email, _client_ip())
            flash("Invalid username or password", "error")
        except Exception:
            error_logger.exception('Error during login processing | email=%s', email)
            flash('Unable to process login right now. Please try again.', 'error')
            return redirect(url_for('auth.login'))

    captcha_question = generate_math_captcha()
    return render_template('auth/login.html', form=form, captcha_question=captcha_question)

@blp.route('/register', methods=['GET','POST'])
def register():
    access_logger.info(
        'Route accessed | action=auth.register | method=%s | path=%s | ip=%s',
        request.method,
        request.path,
        _client_ip()
    )
    form = RegisterForm()
    if request.method == "POST":
        try:            
            full_name=request.form.get('full_name')
            email=request.form.get('email').strip().lower()
            password=decrypt_password(request.form.get('password'))
            state_id=request.form.get('state')
            district_id=request.form.get('district')
            block_id=request.form.get('block')
            user_duplicate_check = User.get_user_by_email(email)
            if user_duplicate_check:
                activity_logger.warning('Registration attempt with existing email | email=%s | ip=%s', email, _client_ip())
                flash(message="Email already registered. Please login or use a different email.", category="error")
                return redirect(url_for('auth.register'))
            user = User(name=full_name, 
                        email=email,
                        password=pbkdf2_sha256.hash(password), 
                        state_id=int(state_id), 
                        district_id=None if int(district_id) == -1 else int(district_id),
                        block_id=None if int(block_id) == -1 else int(block_id))
            user.save()
            # give normal user role 
            user_registered = User.get_user_by_email(email)
            
            if user_registered is None:
                error_logger.error('User registration failed | reason=user_not_found_post_create | email=%s', email)
                flash(message="There was a problem in registering. Please try again.", category="error")
                return redirect(url_for('auth.register'))
            user_in_role = UserInRole(user_id=user_registered.id, role_id=2) # default role as 'user'
            user_in_role.save()
            activity_logger.info('Registration submission | email=%s | ip=%s', email, _client_ip())
            flash(message=f"Registered Successfully. Please login with your credentials", category="success")
            return redirect(url_for('auth.login'))
        except Exception as ex:
            error_logger.exception('Error during registration | email=%s', request.form.get('email'))
            flash(message=f"There was a problem in registering", category="error")
            return redirect(url_for('auth.register'))
    captcha_question = generate_math_captcha()    
    return render_template('auth/register.html', form=form, captcha_question=captcha_question)


@blp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    access_logger.info(
        'Route accessed | action=auth.change_password | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id
    )
    uuid = current_user.id
    form = ChangePasswordForm()

    if request.method == "POST":
        try:
            current_pwd = decrypt_password(request.form.get('old_password', ''))
            new_pass_input = decrypt_password(request.form.get('password', ''))
            confirm_pass_input = decrypt_password(request.form.get('confirm_password', ''))
            
            if not current_pwd or not (8 <= len(current_pwd) <= 32):
                flash('Current password is required and must be 8-32 characters.', 'error')
                return render_template('change_password.html', uuid=uuid)        
            
            password_pattern = re.compile(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,32}$'
            )
            if not new_pass_input or not password_pattern.match(new_pass_input):
                flash(
                    'New password must be 8-32 characters, include upper and lower case letters, a digit, and a special character.','error'
                )
                return render_template('change_password.html', uuid=uuid)
            
            if new_pass_input != confirm_pass_input:
                flash("Both passwords do not match.", 'warning')
                return render_template('auth/change_password.html', uuid=uuid)
            
            new_pass = pbkdf2_sha256.hash(new_pass_input)
            user = User.query.filter_by(id=uuid).first()
            if user:
                db_pass = user.password
                hash_check = pbkdf2_sha256.verify(current_pwd, db_pass)
                if hash_check:
                    data = {"password": new_pass}
                    User.update_db(data, user.id)
                    logout_user()
                    activity_logger.info('Password changed | user_id=%s | ip=%s', user.id, _client_ip())
                    flash('Password Changed Successfully. Please login with new password to continue','success')
                    return redirect(url_for('auth.login'))
                flash('Please Check Your Old Password and Try Again !! ', 'error')
                return redirect(url_for('auth.change_password', uuid=uuid))
            error_logger.warning('Password change attempted for missing user | user_id=%s | ip=%s', uuid, _client_ip())
            flash('Unable to locate user account.', 'error')
            return redirect(url_for('auth.change_password', uuid=uuid))
        except Exception:
            error_logger.exception('Error processing change password | user_id=%s', current_user.id)
            flash('Unable to change password right now. Please try again.', 'error')
            return redirect(url_for('auth.change_password', uuid=uuid))
    if request.method == "GET":
        session['password_change_redirected'] = False
        return render_template('auth/change_password.html', uuid=uuid, form=form)

@blp.route('/logout')
@login_required
def logout():
    access_logger.info('Route accessed | action=auth.logout | user_id=%s | ip=%s', current_user.id, _client_ip())
    activity_logger.info('Logout | user_id=%s | ip=%s', current_user.id, _client_ip())
    logout_user()
    return redirect(url_for('routes.index'))


@blp.route('/certificates')
@login_required
def certificates():
    access_logger.info('Route accessed | action=auth.certificates | user_id=%s | ip=%s', current_user.id, _client_ip())

    certificates = UserCourse.get_user_certificates(current_user.id)
    # certificates = [{"course_name":"Participatory Rural Planning Using Yuktdhara",
    #                 "course_description":"An engaging introduction to Yuktdhara—India’s geospatial platform for MGNREGA asset planning at the Gram Panchayat level with integrated satellite data and mapping tools.",
    #                 "course_id":1},
    #                 {"course_name":"युक्तधारा पोर्टल के माध्यम से पारदर्शी ग्रामीण योजना",
    #                  "course_description":"युक्तधारा वीडियो में युक्त धारा पोर्टल की कार्यप्रणाली और विशेषताएं सरल व प्रभावी तरीके से प्रस्तुत की गई हैं, जो ग्रामीण Panchayat स्तर पर MGNREGA की योजना निर्माण को GIS आधारित बहुआयामी दृष्टिकोण प्रदान करती है।",
    #                  "course_id":2},
    #                 {"course_name":"The Rural Employment Framework",
    #                  "course_description":"A structured guide to rights, responsibilities, and planning under Mahatma Gandhi National Rural Employment Guarantee Act.",
    #                 "course_id":3},
    #                 {"course_name":"Introduction to Geospatial Mapping and Scientific Planning",
    #                  "course_description":"Unlock the power of geospatial tools—learn to use base maps, Bhuvan, and WMS for smart MGNREGA asset planning.",
    #                  "course_id":4}
    #                 ]
    return render_template('auth/certificates.html', certificates=certificates)


@blp.route('/print_certificate/<int:course_id>')
@login_required
def print_certificate(course_id):
    access_logger.info(
        'Route accessed | action=auth.print_certificate | user_id=%s | course_id=%s | ip=%s',
        getattr(current_user, 'id', None),
        course_id,
        _client_ip()
    )
    user_course = UserCourse.get_certificate_details(current_user.id, course_id)
        
    if not user_course:
        flash('Certificate not found or not yet earned for this course.', 'error')
        return redirect(url_for('auth.certificates'))

    user = {
        "name": user_course.get('user_name'),
        "completion_time": user_course.get('certificate_timestamp').strftime("%d %B %Y"),
        "print_date_time": datetime.datetime.now().strftime("%d %B %Y, %I:%M %p"),
        "uuid": user_course.get('user_uuid')
    }
    certificate = {
        "name": user_course.get('course_name'),
        "background": 'assets/certificate_bg_2.png' if course_id in [3, 4, 6] else 'assets/certificate_bg.png',
        "topics": user_course.get('course_topics', '').split(',') if user_course.get('course_topics') else [],
        "course_id": course_id
    }
    
    return render_template(
        'lms/certificate.html',
        certificate=certificate,
        user=user
    )
    
@blp.route('/update_profile',methods=['GET','POST'])
def update_profile():
    access_logger.info(
        'Route accessed | action=auth.update_profile | method=%s | path=%s | ip=%s | user_id=%s',
        request.method,
        request.path,
        _client_ip(),
        current_user.id if current_user.is_authenticated else 'anonymous'
    )
    profile = None
    if current_user.is_authenticated:
        profile = User.get_user_by_id(current_user.id)
    form = ProfileForm(obj=profile)
    if request.method == "POST":
        email = request.form.get('email', '').strip()
        name = request.form.get('full_name', '').strip()
        state_id = request.form.get('state','').strip()
        district_id = request.form.get('district','').strip()
        block_id = request.form.get('block','').strip() 
        captcha_response = request.form.get('captcha_answer','').strip()

        if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            activity_logger.warning('Profile update validation failed | reason=email | user=%s | ip=%s', email, _client_ip())
            flash('Please enter a valid email address.','danger')
            return redirect(url_for('auth.update_profile'))
        if not name or not re.match(r'^[A-Za-z0-9_ ]{3,20}$', name):
            activity_logger.warning('Profile update validation failed | reason=name | user=%s | ip=%s', email, _client_ip())
            flash('Username must be 3-20 characters, only letters, numbers, underscores, and spaces.','danger')
            return redirect(url_for('auth.update_profile'))
        
        if not captcha_response:
            activity_logger.warning('Profile update validation failed | reason=captcha_missing | user=%s | ip=%s', email, _client_ip())
            flash('Please fill the captcha.','danger')
            return redirect(url_for('auth.update_profile'))
        
        if district_id == '-1':
            district_id = None
        if block_id == '-1':
            block_id = None
        
        captcha_answer = int(session.get('captcha_answer'))
        captcha_response = int(captcha_response)
        verification_response = captcha_answer == captcha_response
        if not verification_response:
            activity_logger.warning('Profile update captcha failed | user=%s | ip=%s', email, _client_ip())
            flash('CAPTCHA verification failed. Please try again.','danger')
            return redirect(url_for('auth.update_profile'))

        try:
            user = User.query.filter_by(email=email).first()
            if user:
                user.name = name
                user.state_id = state_id
                user.district_id = district_id
                user.block_id = block_id
                db.session.commit()
                activity_logger.info('Profile updated | user_id=%s | ip=%s', user.id, _client_ip())
            else:
                activity_logger.warning('Profile update attempted for unknown email | email=%s | ip=%s', email, _client_ip())
            flash("You have Successfully updated your profile.","success")
        except Exception:
            db.session.rollback()
            error_logger.exception('Error updating profile | email=%s', email)
            flash('Unable to update profile at this time.', 'error')
        return redirect(url_for('auth.update_profile'))
    states = State_UT.get_states()
    form.state.choices = [(0, '-- Select State --')] + \
                        [(str(s.id), s.name.upper()) for s in states]  
    
    if current_user.is_authenticated:
        profile = User.get_user_by_id(current_user.id)
        # profile = profile.json()
        form.state.data = str(profile.state_id)

        districts = District.query.filter_by(state_id=profile.state_id).all()
        form.district.choices = [(0, '-- Select District --')] + \
                                [(str(d.id), d.name.upper()) for d in districts]
        form.district.data = str(profile.district_id)
        
        blocks = Block.query.filter_by(state_id=profile.state_id, district_id=profile.district_id).all()
        form.block.choices = [(0, '-- Select block --')] + \
                                [(str(b.id), b.name.upper()) for b in blocks]
        form.block.data = str(profile.block_id)
        form.full_name.data = profile.name
        form.email.data = profile.email

    captcha_question = generate_math_captcha()
    return render_template('other/profile.html', form = form, captcha_question=captcha_question, 
                            states=states, user_data=profile)
