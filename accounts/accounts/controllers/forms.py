"""Provides forms for login, registration, etc."""

# from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, \
    SelectMultipleField, BooleanField, Form, HiddenField
from wtforms.validators import DataRequired, Email, Length, URL, optional
from wtforms.widgets import ListWidget, CheckboxInput, Select
import pycountry

# from .. import domain
from accounts.domain import UserRegistration
from arxiv import taxonomy, users
from .util import MultiCheckboxField, OptGroupSelectField


class LoginForm(Form):
    """Log in form."""

    username = StringField('Username or e-mail', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
