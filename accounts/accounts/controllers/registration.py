"""
Controllers for registration and user profile management.

WORK IN PROGRESS: not in use.

Users are able to create a new arXiv account, and login using their username
and password. Each user can create a personalized profile with contact and
affiliation information, and links to external identities such as GitHub and
ORCID.
"""

from typing import Dict, Tuple, Any, Optional
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import BadRequest, InternalServerError

from arxiv import status
from arxiv_auth import domain
from arxiv.base import logging
from arxiv_auth import domain

from arxiv_auth.auth.sessions import SessionStore

from wtforms import StringField, PasswordField, SelectField, \
    BooleanField, Form, HiddenField
from wtforms.validators import DataRequired, Email, Length, URL, optional, \
    ValidationError
from flask import url_for, Markup
import pycountry

from arxiv import taxonomy
from .util import MultiCheckboxField, OptGroupSelectField

from .. import stateless_captcha

from arxiv_auth.legacy import accounts
from arxiv_auth.legacy.exceptions import RegistrationFailed, SessionCreationFailed, SessionDeletionFailed

logger = logging.getLogger(__name__)

ResponseData = Tuple[dict, int, dict]


def _login_classic(user: domain.User, auth: domain.Authorizations,
                   ip: Optional[str]) -> Tuple[domain.Session, str]:
    try:
        c_session = legacy.create(auth, ip, ip, user=user)
        c_cookie = legacy.generate_cookie(c_session)
        logger.debug('Created classic session: %s', c_session.session_id)
    except SessionCreationFailed as e:
        logger.debug('Could not create classic session: %s', e)
        raise InternalServerError('Cannot log in') from e  # type: ignore
    return c_session, c_cookie


def _logout(session_id: str) -> None:
    sessions = SessionStore.current_session()
    try:
        sessions.delete_by_id(session_id)
    except SessionDeletionFailed as e:
        logger.debug('Could not delete session %s', session_id)
        raise InternalServerError('Cannot logout') from e  # type: ignore
    return None


def _login(user: domain.User, auth: domain.Authorizations, ip: Optional[str]) \
        -> Tuple[domain.Session, str]:
    sessions = SessionStore.current_session()
    try:
        session = sessions.create(auth, ip, ip, user=user)
        cookie = sessions.generate_cookie(session)
        logger.debug('Created session: %s', session.session_id)
    except SessionCreationFailed as e:
        logger.debug('Could not create session: %s', e)
        raise InternalServerError('Cannot log in') from e  # type: ignore
    return session, cookie


def register(method: str, params: MultiDict, captcha_secret: str, ip: str,
             next_page: str) -> ResponseData:
    """Handle requests for the registration view."""
    data: Dict[str, Any]
    if method == 'GET':
        captcha_token = stateless_captcha.new(captcha_secret, ip)
        _params = MultiDict({'captcha_token': captcha_token})  # type: ignore
        form = RegistrationForm(_params, next_page=next_page)
        form.configure_captcha(captcha_secret, ip)
        data = {'form': form, 'next_page': next_page}
    elif method == 'POST':
        logger.debug('Registration form submitted')
        form = RegistrationForm(params, next_page=next_page)
        data = {'form': form, 'next_page': next_page}
        form.configure_captcha(captcha_secret, ip)

        if not form.validate():
            logger.debug('Registration form not valid')
            return data, status.HTTP_400_BAD_REQUEST, {}

        logger.debug('Registration form is valid')
        password = form.password.data

        # Perform the actual registration.
        try:
            user, auth = accounts.register(form.to_domain(), password, ip, ip)
        except RegistrationFailed as e:
            msg = 'Registration failed'
            raise InternalServerError(msg) from e  # type: ignore

        # Log the user in.
        session, cookie = _login(user, auth, ip)
        c_session, c_cookie = _login_classic(user, auth, ip)
        data.update({
            'cookies': {
                'session_cookie': (cookie, session.expires),
                'classic_cookie': (c_cookie, c_session.expires)
            },
            'user_id': user.user_id
        })
        return data, status.HTTP_303_SEE_OTHER, {'Location': next_page}
    return data, status.HTTP_200_OK, {}


def view_profile(user_id: str, session: domain.Session) -> ResponseData:
    """Handle requests to view a user's profile."""
    user = accounts.get_user_by_id(user_id)
    return {'user': user}, status.HTTP_200_OK, {}


def edit_profile(method: str, user_id: str, session: domain.Session,
                 params: Optional[MultiDict] = None,
                 ip: Optional[str] = None) -> ResponseData:
    """Handle requests to update a user's profile."""
    if method == 'GET':
        user = accounts.get_user_by_id(user_id)
        form = ProfileForm.from_domain(user)
        data = {'form': form, 'user_id': user_id}
    elif method == 'POST':
        form = ProfileForm(params)
        data = {'form': form, 'user_id': user_id}

        try:
            if not form.validate():
                return data, status.HTTP_400_BAD_REQUEST, {}
        except ValueError:
            return data, status.HTTP_400_BAD_REQUEST, {}

        if form.user_id.data != user_id:
            msg = 'User ID in request does not match'
            raise BadRequest(msg)  # type: ignore

        user = form.to_domain()
        try:
            user, auth = accounts.update(user)
        except Exception as e:
            data['error'] = 'Could not save user profile; please try again'
            return data, status.HTTP_500_INTERNAL_SERVER_ERROR, {}

        # We need a new session, to update user's data.
        _logout(session.session_id)
        new_session, new_cookie = _login(user, auth, ip)
        data.update({'cookies': {
            'session_cookie': (new_cookie, new_session.expires)
        }})
        return data, status.HTTP_303_SEE_OTHER, {}
    return data, status.HTTP_200_OK, {}


class ProfileForm(Form):
    """User registration form."""

    COUNTRIES = [('', '')] + \
        [(country.alpha_2, country.name) for country in pycountry.countries]
    RANKS = [('', '')] + domain.RANKS
    GROUPS = [
        (key, group['name'])
        for key, group in taxonomy.definitions.GROUPS.items()
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

    user_id = HiddenField('User ID')

    forename = StringField('First or given name',
                           validators=[Length(min=1, max=50), DataRequired()])
    surname = StringField('Last or family name',
                          validators=[Length(min=1, max=50), DataRequired()])
    suffix = StringField('Suffix', validators=[Length(max=50)])
    affiliation = StringField(
        'Affiliation',
        validators=[Length(max=255), DataRequired()],
        description='This field accepts '
                    '<a href="https://arxiv.org/tex_accents">'
                    'pidgin TeX (\\\'o)</a> for foreign characters.'
    )
    country = SelectField('Country', choices=COUNTRIES,
                          validators=[DataRequired()])
    status = SelectField('Academic Status', choices=RANKS,
                         validators=[DataRequired()])

    groups = MultiCheckboxField('Group(s) to which you would like to submit',
                                choices=GROUPS, default='')
    default_category = OptGroupSelectField('Your default category',
                                           choices=CATEGORIES, default='')

    url = StringField('Your homepage URL', validators=[optional(),
                      Length(max=255), URL()])
    remember_me = BooleanField('Have your browser remember who you are?',
                               default=True)

    @classmethod
    def from_domain(cls, user: domain.User) -> 'ProfileForm':
        """Instantiate this form with data from a domain object."""
        return cls(MultiDict({  # type: ignore
            'username': user.username,
            'email': user.email,
            'forename': user.name.forename,
            'surname': user.name.surname,
            'suffix': user.name.suffix,
            'affiliation': user.profile.affiliation,
            'country': user.profile.country.upper(),
            'status': user.profile.rank,
            'groups': user.profile.submission_groups,
            'default_category': user.profile.default_category.compound,
            'url': user.profile.homepage_url,
            'remember_me': user.profile.remember_me
        }))

    def to_domain(self) -> domain.User:
        """Generate a :class:`.User` from this form's data."""
        return domain.User(
            user_id=self.user_id.data if self.user_id.data else None,
            username=self.username.data,
            email=self.email.data,
            name=domain.UserFullName(
                forename=self.forename.data,
                surname=self.surname.data,
                suffix=self.suffix.data
            ),
            profile=domain.UserProfile(
                affiliation=self.affiliation.data,
                country=self.country.data,
                rank=int(self.status.data),     # WTF can't handle int values.
                submission_groups=self.groups.data,
                default_category=domain.Category(
                    *self.default_category.data.split('.')
                ),
                homepage_url=self.url.data,
                remember_me=self.remember_me.data
            )
        )


class RegistrationForm(Form):
    """User registration form."""

    email = StringField(
        'Email address',
        validators=[Email(), Length(max=255), DataRequired()],
        description="You must be able to receive mail at this address."
        " We take <a href='https://arxiv.org/help/email-protection'>"
        " strong measures</a> to protect your email address from viruses and"
        " spam. Do not enter an e-mail address that belongs to someone"
        " else: if we discover that you've done so, we will suspend your"
        " account."
    )

    username = StringField('Username',
                           validators=[Length(min=5, max=20), DataRequired()],
                           description='Please choose a username between 5 and'
                                       ' 20 characters in length.')

    password = PasswordField(
        'Password',
        validators=[Length(min=8, max=20), DataRequired()],
        description="Please choose a password that is between 8 and 20"
                    " characters in length. Longer passwords are more secure."
                    " You may use alphanumeric characters, as well as"
                    " <code>* @ # $ ! ? %</code>.")
    password2 = PasswordField(
        'Re-enter password',
        validators=[Length(min=8), DataRequired()],
        description="Your passwords must match.")

    captcha_value = StringField('Are you a robot?',
                                validators=[DataRequired()],
                                description="Please enter the text that you"
                                            " see in the image above")
    captcha_token = HiddenField()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Grab `next_page` param, if provided."""
        self.next_page = kwargs.pop('next_page', None)
        super(RegistrationForm, self).__init__(*args, **kwargs)

    def configure_captcha(self, captcha_secret: str, ip: str) -> None:
        """Set configuration details for the stateless_captcha."""
        self.captcha_secret = captcha_secret
        self.ip = ip

    def validate_username(self, field: StringField) -> None:
        """Ensure that the username is unique."""
        if accounts.does_username_exist(field.data):
            raise ValidationError(Markup(
                f'An account with that email already exists. You can try'
                f' <a href="{url_for("ui.login")}?next_page={self.next_page}">'
                f' logging in</a>, or <a href="{url_for("lost_password")}">'
                f' reset your password </a>.'
            ))

    def validate_email(self, field: StringField) -> None:
        """Ensure that the email address is unique."""
        if accounts.does_email_exist(field.data):
            raise ValidationError(Markup(
                f'An account with that email already exists. You can try'
                f' <a href="{url_for("ui.login")}?next_page={self.next_page}">'
                f' logging in</a>, or <a href="{url_for("lost_password")}">'
                f' reset your password </a>.'
            ))

    def validate_captcha_value(self, field: StringField) -> None:
        """Check the captcha value against the captcha token."""
        try:
            stateless_captcha.check(self.captcha_token.data, field.data,
                                    self.captcha_secret, self.ip)
        except (stateless_captcha.InvalidCaptchaValue,
                stateless_captcha.InvalidCaptchaToken) as e:
            # Get a fresh captcha challenge. More than likely the user is
            # having trouble interpreting the challenge,
            token = stateless_captcha.new(self.captcha_secret, self.ip)
            self.captcha_token.data = token

            # It is convenient to provide feedback to the user via the
            # form, so we'll do that here if the captcha doesn't check out.
            self.captcha_value.data = ''    # Clear the field.
            raise ValidationError('Please try again')

    def validate_password(self, field: StringField) -> None:
        """Verify that the password is the same in both fields."""
        if self.password.data != self.password2.data:
            raise ValidationError('Passwords must match')

    @classmethod
    def from_domain(cls, user: domain.User) -> 'RegistrationForm':
        """Instantiate this form with data from a domain object."""
        return cls(MultiDict({  # type: ignore
            'username': user.username,
            'email': user.email,
        }))

    def to_domain(self) -> domain.User:
        """Generate a :class:`.User` from this form's data."""
        return domain.User(
            user_id=None,
            username=self.username.data,
            email=self.email.data,
        )
