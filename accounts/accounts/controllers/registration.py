from typing import Dict, Tuple, Any, Optional
import uuid
from werkzeug import MultiDict, ImmutableMultiDict
from werkzeug.exceptions import BadRequest, InternalServerError
from flask import url_for

from arxiv import status
from arxiv.users import domain
from arxiv.base import logging
from accounts.services import legacy, sessions, users

from wtforms import StringField, PasswordField, SelectField, \
    SelectMultipleField, BooleanField, Form, HiddenField
from wtforms.validators import DataRequired, Email, Length, URL, optional, \
    ValidationError
from wtforms.widgets import ListWidget, CheckboxInput, Select
import pycountry

# from .. import domain
from arxiv import taxonomy
from .util import MultiCheckboxField, OptGroupSelectField

from .. import stateless_captcha

logger = logging.getLogger(__name__)

ResponseData = Tuple[dict, int, dict]


def register(method: str, params: MultiDict, captcha_secret: str, ip: str) \
        -> ResponseData:
    """Handle requests for the registration view."""
    if method == 'GET':
        captcha_token = stateless_captcha.new(captcha_secret, ip)
        _params = MultiDict({'captcha_token': captcha_token})  # type: ignore
        form = RegistrationForm(_params)
        form.configure_captcha(captcha_secret, ip)
        data = {'form': form}
    elif method == 'POST':
        logger.debug('Registration form submitted')
        form = RegistrationForm(params)
        data = {'form': form}
        form.configure_captcha(captcha_secret, ip)
        if not form.validate():
            return data, status.HTTP_400_BAD_REQUEST, {}

        logger.debug('Form is valid')
        user, auth = users.register(form.to_domain(), ip, ip)
        try:
            session, cookie = sessions.create(user, auth, ip, ip)
            logger.debug('Created session: %s', session.session_id)
            c_session, c_cookie = legacy.create(user, auth, ip, ip)
            logger.debug('Created classic session: %s',
                         c_session.session_id)
        except legacy.exceptions.SessionCreationFailed as e:
            logger.debug('Could not create session: %s', e)
            raise InternalServerError('Cannot log in') from e  # type: ignore

        data.update({'session_cookie': cookie, 'classic_cookie': c_cookie})
        headers = {'Location': url_for('ui.profile')}
        return data, status.HTTP_303_SEE_OTHER, headers
    return data, status.HTTP_200_OK, {}


class RegistrationForm(Form):
    """User registration form."""

    COUNTRIES = [('', '')] + \
        [(country.alpha_2, country.name) for country in pycountry.countries]
    RANKS = [('', '')] + domain.UserProfile.RANKS
    GROUPS = [
        (key, group['name']) for key, group in taxonomy.GROUPS.items()
        if not group.get('is_test', False)
    ]
    CATEGORIES = [
        (archive['name'], [
            (category_id, category['name'])
            for category_id, category in taxonomy.CATEGORIES_ACTIVE.items()
            if category['in_archive'] == archive_id
        ])
        for archive_id, archive in taxonomy.ARCHIVES_ACTIVE.items()
    ]
    """Categories grouped by archive."""

    email = StringField(
        'Email address',
        validators=[Email(), Length(max=255), DataRequired()],
        description="You must be able to receive mail at this address to"
        " register. We take <a href='https://arxiv.org/help/email-protection'>"
        " strong measures</a> to protect your email address from viruses and"
        " spam. Do not register with an e-mail address that belongs to someone"
        " else: if we discover that you've done so, we will suspend your"
        " account."
    )

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
    organization = StringField(
        'Organization',
        validators=[Length(max=255), DataRequired()],
        description='This field accepts '
                    '<a href="https://arxiv.org/user/tex_accents">'
                    'pidgin TeX (\\\'o)</a> for foreign characters.'
    )
    country = SelectField('Country', choices=COUNTRIES,
                          validators=[DataRequired()])
    status = SelectField('Status', choices=RANKS, validators=[DataRequired()])

    groups = MultiCheckboxField('Group(s) to which you would like to submit',
                                choices=GROUPS, default='')
    default_category = OptGroupSelectField('Your default category',
                                           choices=CATEGORIES, default='')

    url = StringField('Your homepage URL', validators=[optional(),
                      Length(max=255), URL()])
    remember_me = BooleanField('Have your browser remember who you are?',
                               default=True)

    captcha_value = StringField('Are you a robot?',
                                validators=[DataRequired()],
                                description="Please enter the text that you"
                                            " see in the image above")
    captcha_token = HiddenField()

    def configure_captcha(self, captcha_secret: str, ip_address: str) -> None:
        """Set configuration details for the stateless_captcha."""
        self.captcha_secret = captcha_secret
        self.ip_address = ip_address

    def to_domain(self) -> domain.UserRegistration:
        """Generate a :class:`.UserRegistration` from this form's data."""
        return domain.UserRegistration(
            username=self.username.data,
            password=self.password.data,
            email=self.email.data,
            name=domain.UserFullName(
                forename=self.forename.data,
                surname=self.surname.data,
                suffix=self.suffix.data
            ),
            profile=domain.UserProfile(
                organization=self.organization.data,
                country=self.country.data,
                rank=int(self.status.data),     # WTF can't handle int values.
                submission_groups=self.groups.data,
                default_category=domain.Category(
                    *self.default_category.data.split()
                ),
                homepage_url=self.url.data,
                remember_me=self.remember_me.data
            )
        )

    def validate_captcha_value(self, field: StringField) -> None:
        """Check the captcha value against the captcha token."""
        try:
            stateless_captcha.check(self.captcha_token.data, field.data,
                                    self.captcha_secret, self.ip_address)
        except (stateless_captcha.InvalidCaptchaValue,
                stateless_captcha.InvalidCaptchaToken) as e:
            # Get a fresh captcha challenge. More than likely the user is
            # having trouble interpreting the challenge,
            token = stateless_captcha.new(self.captcha_secret, self.ip_address)
            self.captcha_token.data = token

            # It is convenient to provide feedback to the user via the
            # form, so we'll do that here if the captcha doesn't check out.
            self.captcha_value.data = ''    # Clear the field.
            raise ValidationError('Please try again')

    def validate_username(self, field: StringField) -> None:
        """Ensure that the username is unique."""
        if users.username_exists(field.data):
            raise ValidationError('An account with that username already'
                                  ' exists')

    def validate_email(self, field: StringField) -> None:
        """Ensure that the email address is unique."""
        if users.email_exists(field.data):
            raise ValidationError('An account with that email address'
                                  ' already exists')
