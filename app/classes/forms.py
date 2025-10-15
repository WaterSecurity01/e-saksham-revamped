from typing import Optional
from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, FileField, PasswordField, RadioField, SelectField, StringField, SubmitField, TextAreaField, IntegerField, ValidationError
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, InputRequired, optional
from flask_wtf.file import FileField, FileRequired, FileAllowed, FileStorage, file_size

from app.models.menu_item import MenuItem


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    captcha_answer = StringField(
        "Captcha Answer",
        validators=[DataRequired(), Length(max=3)]
    )
    submit = SubmitField(
        "Login", name="submitBtn"
        )


class RegisterForm(FlaskForm):
    full_name = StringField(
        "Full Name (for Certificate)",
        validators=[DataRequired(), Length(min=3, max=100)]
    )

    state = SelectField(
        "State",
        choices=[],  # filled dynamically via JS
        validators=[DataRequired()]
    )

    district = SelectField(
        "District",
        choices=[],  # empty at load, enabled dynamically
        validators=[DataRequired()]
    )

    block = SelectField(
        "Block",
        choices=[],  # empty at load, enabled dynamically
        validators=[DataRequired()]
    )

    email = EmailField(
        "Email (username)",
        validators=[DataRequired(), Email(), Length(max=120)]
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])',
                message="Password must contain at least one lowercase, one uppercase, one digit, and one special character."
            )
        ]
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )

    captcha_answer = StringField(
        "Captcha Answer",
        validators=[DataRequired(), Length(max=3)]
    )

    submit = SubmitField(
        "Register", name="submitBtn"
        )

class ProfileForm(FlaskForm):
    full_name = StringField("Full Name (for Certificate)",validators=[DataRequired(), Length(min=3, max=100)])
    state = SelectField("State",choices=[],  validators=[DataRequired()])
    district = SelectField("District",choices=[],  validators=[DataRequired()])
    block = SelectField("Block",choices=[],  validators=[DataRequired()])
    email = EmailField("Email (username)", validators=[DataRequired(), Email(), Length(max=120)])
    captcha_answer = StringField("Captcha Answer", validators=[DataRequired(), Length(max=3)])
    submit = SubmitField("Update Profile", name="submitBtn")

class UploadForm(FlaskForm):
    scorm_file = FileField(
        'SCORM Package (ZIP file)',
        validators=[
            FileRequired(message="Please upload a SCORM package."),
            FileAllowed(['zip'], 'Only .zip files are allowed!')
        ]
    )

    course_title = StringField(
        "Course Title",
        validators=[DataRequired(), Length(min=3, max=100)]
    )
    short_name = StringField(
        "Short Name",
        validators=[DataRequired(), Length(min=3, max=50)]
    )
    
    description = TextAreaField(
        'Course Description',
        validators=[DataRequired(),
            Length(max=500, message="Description must be under 500 characters.")
        ],
        render_kw={"rows": 10}
    )
    topics = TextAreaField(
        'Course Topics',
        validators=[DataRequired(),
            Length(max=500, message="Topics must be under 500 characters.")
        ],
        render_kw={"rows": 10}
    )
    
    submit = SubmitField('Upload Course', name='uploadBtn', id='uploadBtn')

class RoleForm(FlaskForm):
    name = StringField("Role Name", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])
    submit = SubmitField("Add Role")

def not_default(form, field):
    if field.data == -1:
        raise ValidationError("Please select a parent")

class menuItemForm(FlaskForm):
    name = StringField("Menu Item", validators=[DataRequired()])
    url = StringField("url", validators=[DataRequired()])
    icon = StringField("Icon", validators=[DataRequired()])
    parent_id = SelectField(u"Parent", choices=[], coerce=int, validators=[InputRequired(), not_default])
    order_index = IntegerField("Order Index", validators=[DataRequired()])
    submit = SubmitField("Add Menu Item")

class FeedbackForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = EmailField("Email (username)",validators=[DataRequired(), Email(), Length(max=120)])
    subject = StringField("Subject", validators=[DataRequired()])
    message_type = SelectField("District", choices=[('-1','Select message category'),('course','Course feedback'),('technical', 'Technical(IT) related problem reporting'),
                                                    ('subject_related','Subject related issues'),('admin','Admin or other broader concerns'),('others','Others')],  validators=[DataRequired()])
    message = TextAreaField('Message',validators=[Length(max=500, message="Description must be under 500 characters.")],render_kw={"rows": 3})
    feedback_image = FileField('SCORM Package (ZIP file)',validators=[FileRequired(message="Please upload a screenshot here"),FileAllowed(['jpg','jpeg','png'], 'Only .zip files are allowed!')])
    captcha_answer = StringField("Captcha Answer",validators=[DataRequired(), Length(max=3)])
    submit = SubmitField("Submit", name="submitBtn")

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    captcha_answer = StringField(
        "Captcha Answer",
        validators=[DataRequired(), Length(max=3)]
    )
    submit = SubmitField("Submit", name="submitBtn")

