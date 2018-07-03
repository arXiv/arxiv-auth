from typing import Tuple, Optional
from werkzeug import MultiDict
from werkzeug.exceptions import BadRequest
from wtforms import StringField, PasswordField, SelectField, \
    SelectMultipleField, BooleanField, Form, HiddenField
from wtforms.validators import DataRequired, Email, Length, URL, optional, \
    ValidationError
from wtforms.widgets import ListWidget, CheckboxInput, Select
import pycountry

from flask import url_for

from arxiv import taxonomy
from arxiv import status
from arxiv.users import domain
from accounts.services import users
from .util import MultiCheckboxField, OptGroupSelectField


ResponseData = Tuple[dict, int, dict]


def view_profile(user_id: str) -> ResponseData:
    user = users.get_user_by_id(user_id)
    return {'user': user}, status.HTTP_200_OK, {}


def edit_profile(method: str, user_id: str,
                 params: Optional[MultiDict] = None,
                 ip_address: Optional[str] = None) -> ResponseData:
    if method == 'GET':
        user = users.get_user_by_id(user_id)
        form = ProfileForm.from_domain(user)
        data = {'form': form, 'user_id': user_id}
    elif method == 'POST':
        form = ProfileForm(params)
        data = {'form': form, 'user_id': user_id}
        if form.validate():
            if form.user_id.data != user_id:
                raise BadRequest('User ID in request does not match')
            user = form.to_domain()
            try:
                users.update_user(user)
            except Exception as e:
                data['error'] = 'Could not save user profile; please try again'
                return data, status.HTTP_500_INTERNAL_SERVER_ERROR, {}
            headers = {'Location': url_for('ui.view_profile', user_id=user_id)}
            return {}, status.HTTP_303_SEE_OTHER, headers
    return data, status.HTTP_200_OK, {}


class ProfileForm(Form):
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

    user_id = HiddenField('User ID')

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
                           validators=[Length(min=5, max=20), DataRequired()])
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

    @classmethod
    def from_domain(cls, user: domain.User) -> 'ProfileForm':
        """Instantiate this form with data from a domain object."""
        return cls(MultiDict({
            'username': user.username,
            'email': user.email,
            'forename': user.name.forename,
            'surname': user.name.surname,
            'suffix': user.name.suffix,
            'organization': user.profile.organization,
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
            user_id=self.user_id.data,
            username=self.username.data,
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
