import re
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user,login_manager
from app.classes.forms import LoginForm, RegisterForm
from app.classes.helper import decrypt_password, generate_math_captcha
from app.models import User
from passlib.hash import pbkdf2_sha256


blp = Blueprint('auth', __name__, url_prefix='/auth')

@blp.route('/login', methods=['GET','POST'])
def login():
    # Already logged in → redirect
    if current_user.is_authenticated:
        return redirect(url_for('routes.courses'))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.username.data.strip().lower()
        password = decrypt_password(form.password.data or "")
        captcha_response = request.form.get('captcha_answer','').strip()

        # Check CAPTCHA first
        expected_captcha = session.get('captcha_answer')
        if not expected_captcha or captcha_response != expected_captcha:
            flash("Invalid CAPTCHA answer. Please try again.", "danger")
            captcha_question = generate_math_captcha()
            return render_template('auth/login.html', form=form, captcha_question=captcha_question)


        user = User.get_user_by_email(email)

        if user and pbkdf2_sha256.verify(password, user.password):
            login_user(user, remember=form.remember_me.data)
            session.pop('captcha_answer', None)  # clear captcha on success

            # Flask-Login handles secure cookie sessions automatically
            next_page = request.args.get('next')
            return redirect(next_page or url_for('routes.courses'))
        # else send message to the frontend
        flash("Invalid username or password", "error")

    captcha_question = generate_math_captcha()
    return render_template('auth/login.html', form=form, captcha_question=captcha_question)

@blp.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if request.method == "POST":
        try:            
            full_name=request.form.get('full_name')
            email=request.form.get('email')
            password=decrypt_password(request.form.get('password'))
            state_id=request.form.get('state')
            district_id=request.form.get('district')
            block_id=request.form.get('block')
            user = User(name=full_name, 
                        email=email,
                        password=pbkdf2_sha256.hash(password), 
                        state_id=state_id, 
                        district_id=None if district_id == -1 else district_id,
                        block_id=None if block_id == -1 else block_id)
            # user.save()
            flash(message=f"Registered Successfully. Please login with your crendentials", category="success")
            return redirect(url_for('auth.login'))
        except Exception as ex:
            flash(message=f"There was a problem in registering. Error: {ex}", category="error")
            return redirect(url_for('auth.register'))
    captcha_question = generate_math_captcha()    
    return render_template('auth/register.html', form=form, captcha_question=captcha_question)

@blp.route('/logout')
def logout():
    return redirect(url_for('routes.index'))