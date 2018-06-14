"""Provides forms for login, registration, etc."""

# from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, \
    SelectMultipleField, BooleanField, Form
from wtforms.validators import DataRequired, Email, Length, URL, optional
from wtforms.widgets import ListWidget, CheckboxInput, Select

from accounts.domain import UserRegistration, UserFullName, UserProfile
from .util import MultiCheckboxField, OptGroupSelectField


class LoginForm(Form):
    """Log in form."""

    username = StringField('Username or e-mail', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class RegistrationForm(Form):
    """User registration form."""

    COUNTRIES = [('', '')] + UserProfile.COUNTRIES
    RANKS = [('', '')] + UserProfile.RANKS
    GROUPS = UserProfile.GROUPS
    CATEGORIES = UserProfile.CATEGORIES

    email = StringField('Email address',
                        validators=[Email(), Length(max=255), DataRequired()],
                        description=(
        "You must be able to receive mail at this address to register. We take"
        " <a href='https://arxiv.org/help/email-protection'>strong measures"
        "</a> to protect your email address from viruses and spam. Do not"
        " register with an e-mail address that belongs to someone else: if we"
        " discover that you've done so, we will suspend your account."))

    username = StringField('Username',
                           validators=[Length(min=5, max=20), DataRequired()])
    password = PasswordField('Password',
                             validators=[Length(min=6), DataRequired()])
    password2 = PasswordField('Re-enter password',
                              validators=[Length(min=6), DataRequired()])

    forename = StringField('First or given name',
                           validators=[Length(min=1, max=50), DataRequired()])
    surname = StringField('Last or family name',
                          validators=[Length(min=1, max=50), DataRequired()])
    suffix = StringField('Suffix', validators=[Length(max=50)])
    organization = StringField('Organization',
                               validators=[Length(max=255), DataRequired()],
                               description=(
        'This field accepts <a href="https://beta.arxiv.org/user/tex_accents">'
        'pidgin TeX (\\\'o)</a> for foreign characters.'
    ))
    country = SelectField('Country', choices=COUNTRIES,
                          validators=[DataRequired()])
    status = SelectField('Status', choices=RANKS, validators=[DataRequired()])

    groups = MultiCheckboxField('Group(s) to which you would like to submit',
                                choices=GROUPS, default='')
    default_category = OptGroupSelectField('Your default category',
                                           choices=CATEGORIES, default='')

    url = StringField('Your homepage URL', validators=[optional(), Length(max=255), URL()])
    remember_me = BooleanField('Have your browser remember who you are?',
                               default=True)

    def to_domain(self) -> UserRegistration:
        """Generate a :class:`.UserRegistration` from this form's data."""
        return UserRegistration(
            username=self.username.data,
            password=self.password.data,
            email=self.email.data,
            name=UserFullName(
                forename=self.forename.data,
                surname=self.surname.data,
                suffix=self.suffix.data
            ),
            profile=UserProfile(
                organization=self.organization.data,
                country=self.country.data,
                rank=int(self.status.data),     # WTF can't handle int values.
                submission_groups=self.groups.data,
                default_category=self.default_category.data,
                homepage_url=self.url.data,
                remember_me=self.remember_me.data
            )
        )
