"""Defines user concepts for use in arXiv-NG services."""

from typing import Any, Optional, Type, NamedTuple, List, Callable
from datetime import datetime
import dateutil.parser
from pytz import timezone, UTC
from functools import partial
from arxiv import taxonomy
from arxiv.taxonomy import Category

from arxiv.base import logging

logger = logging.getLogger(__name__)
EASTERN = timezone('US/Eastern')


class UserProfile(NamedTuple):
    """User profile data."""

    # mypy (oddly) does not support class attributes:
    #  https://github.com/python/mypy/issues/3959
    STAFF = ('1', 'Staff')  # type: ignore
    PROFESSOR = ('2', 'Professor')  # type: ignore
    POST_DOC = ('3', 'Post doc')  # type: ignore
    GRAD_STUDENT = ('4', 'Grad student')  # type: ignore
    OTHER = ('5', 'Other')  # type: ignore
    RANKS = [STAFF, PROFESSOR, POST_DOC, GRAD_STUDENT, OTHER]  # type: ignore

    affiliation: str
    """Institutional affiliation."""

    country: str
    """Should be an ISO 3166-1 alpha-2 country code."""

    rank: int
    """Academic rank. Must be one of :attr:`UserProfile.RANKS`."""

    submission_groups: List[str]
    """
    Groups to which the user prefers to submit.

    Items should be one of :ref:`arxiv.taxonomy.definitions.GROUPS`.
    """

    default_category: Category
    """
    Default submission category.

    Should be one of :ref:`arxiv.taxonomy.CATEGORIES`.
    """

    homepage_url: str = ''
    """User's homepage or external profile URL."""

    remember_me: bool = True
    """Indicates whether the user prefers permanent session cookies."""

    @property
    def rank_display(self) -> str:
        """The display name of the user's rank."""
        _rank: str = dict(self.RANKS)[str(self.rank)]
        return _rank

    @property
    def default_archive(self) -> str:
        """The archive of the default category."""
        return taxonomy.CATEGORIES[self.default_category]['in_archive']

    @property
    def default_subject(self) -> Optional[str]:
        """The subject of the default category."""
        if '.' in self.default_category:
            return self.default_category.split('.', 1)[1]
        return self.default_category

    @property
    def groups_display(self) -> str:
        """Display-ready representation of active groups for this profile."""
        return ", ".join([
            taxonomy.definitions.GROUPS[group]['name']
            for group in self.submission_groups
        ])


class Scope(NamedTuple):
    """Represents an authorization policy."""

    domain: str
    """
    The domain to which the scope applies.

    This will generally refer to a specific service.
    """

    action: str
    """An action within ``domain`."""

    resource: Optional[str] = None
    """The specific resource to which this policy applies."""

    def __repr__(self) -> str:
        """Return this scope as a :-delimited string."""
        return ":".join([o for o in self if o is not None])

    def __str__(self) -> str:
        """Return this scope as a :-delimited string."""
        return ":".join([o for o in self if o is not None])

    def for_resource(self, resource_id: str) -> 'Scope':
        """Create a copy of this scope with a specific resource."""
        return Scope(self.domain, self.action, resource_id)

    def as_global(self) -> 'Scope':
        """Create a copy of this scope with a global resource."""
        return self.for_resource('*')

    class domains:
        """Known authorization domains."""

        PUBLIC = 'public'
        """The public arXiv site, including APIs."""
        PROFILE = 'profile'
        """arXiv user profile."""
        SUBMISSION = 'submission'
        """Submission interfaces and actions."""
        UPLOAD = 'upload'
        """File uploads, including those for submissions."""
        COMPILE = 'compile'
        """PDF compilation."""
        FULLTEXT = 'fulltext'
        """Fulltext extraction."""

    class actions:
        """Known authorization actions."""

        UPDATE = 'update'
        CREATE = 'create'
        DELETE = 'delete'
        RELEASE = 'release'
        READ = 'read'
        PROXY = 'proxy'


class Authorizations(NamedTuple):
    """Authorization information, e.g. associated with a :class:`.Session`."""

    classic: int = 0
    """Capability code associated with a user's session."""

    endorsements: List[Category] = []
    """Categories to which the user is permitted to submit."""

    scopes: List[Scope] = []
    """Authorized :class:`.scope`s. See also :mod:`arxiv.users.auth.scopes`."""

    def endorsed_for(self, category: Category) -> bool:
        """
        Check whether category is included in this endorsement authorization.

        If a user/client is authorized for all categories in a particular
        archive, the category names in :attr:`Authorization.endorsements` will
        be compressed to a wilcard ``archive.*`` representation. If the
        user/client is authorized for all categories in the system, this will
        be compressed to "*.*".

        Parameters
        ----------
        category : :class:`.Category`

        Returns
        -------
        bool

        """
        archive = category.split(".", 1)[0] if "." in category else category
        return category in self.endorsements \
            or f"{archive}.*" in self.endorsements \
            or "*.*" in self.endorsements

    @classmethod
    def before_init(cls, data: dict) -> None:
        """Make sure that endorsements are :class:`.Category` instances."""
        # Iterative coercion is hard. It's a lot easier to handle this here
        # than to implement a general-purpose coercsion.
        # if self.endorsements and type(self.endorsements[0]) is not Category:
        data['endorsements'] = [
            Category(obj) for obj in data.get('endorsements', [])
        ]
        if 'scopes' in data:
            if type(data['scopes']) is str:
                data['scopes'] = [
                    Scope(*scope.split(':')) for scope
                    in data['scopes'].split()
                ]
            elif type(data['scopes']) is list:
                data['scopes'] = [
                    Scope(**scope) if type(scope) is dict
                    else Scope(*scope.split(':'))
                    for scope in data['scopes']
                ]


class UserFullName(NamedTuple):
    """Represents a user's full name."""

    forename: str
    """First name or given name."""

    surname: str
    """Last name or family name."""

    suffix: str = ''
    """Any title or qualifier used as a suffix/postfix."""


class User(NamedTuple):
    """Represents an arXiv user and their authorizations."""

    username: str
    """Slug-like username."""

    email: str
    """The user's primary e-mail address."""

    user_id: Optional[str] = None
    """Unique identifier for the user. If ``None``, the user does not exist."""

    name: Optional[UserFullName] = None
    """The user's full name (if available)."""

    profile: Optional[UserProfile] = None
    """The user's account profile (if available)."""

    verified: bool = False
    """Whether or not the users' e-mail address has been verified."""

    # TODO: consider whether this information is relevant beyond the
    # ``arxiv.users.legacy.authenticate`` module.
    #
    # approved: bool = True
    # """Whether or not the users' account is approved."""
    #
    # banned: bool = False
    # """Whether or not the user has been banned."""
    #
    # deleted: bool = False
    # """Whether or not the user has been deleted."""


class Client(NamedTuple):
    """API client."""

    owner_id: str
    """The arXiv user responsible for the client."""

    client_id: Optional[str] = None
    """Unique identifier for a :class:`.Client`."""

    name: Optional[str] = None
    """Human-friendly name of the API client."""

    url: Optional[str] = None
    """Homepage or other resource describing the API client."""

    description: Optional[str] = None
    """Brief description of the API client."""

    redirect_uri: Optional[str] = None
    """The authorized redirect URI for the client."""


class Session(NamedTuple):
    """Represents an authenticated session in the arXiv system."""

    session_id: str
    """Unique identifier for the session."""

    start_time: datetime
    """The ISO-8601 datetime when the session was created."""

    user: Optional[User] = None
    """The user for which the session was created."""

    client: Optional[Client] = None
    """The client for which the session was created."""

    end_time: Optional[datetime] = None
    """The ISO-8601 datetime when the session ended."""

    authorizations: Optional[Authorizations] = None
    """Authorizations for the current session."""

    ip_address: Optional[str] = None
    """The IP address of the client for which the session was created."""

    remote_host: Optional[str] = None
    """The hostname of the client for which the session was created."""

    nonce: Optional[str] = None
    """A pseudo-random nonce generated when the session was created."""

    def is_authorized(self, scope: Scope, resource: str) -> bool:
        """Check whether this session is authorized for a specific resource."""
        return (self.authorizations is not None and (
                scope.as_global() in self.authorizations.scopes
                or scope.for_resource(resource) in self.authorizations.scopes))

    @property
    def expired(self) -> bool:
        """Expired if the current time is later than :attr:`.end_time`."""
        return bool(self.end_time is not None
                    and datetime.now(tz=UTC) >= self.end_time)

    @property
    def expires(self) -> Optional[int]:
        """
        Number of seconds until the session expires.

        If the session is already expired, returns 0.
        """
        if self.end_time is None:
            return None
        duration = (self.end_time - datetime.now(tz=UTC)).total_seconds()
        return max(duration, 0)


# Helpers and private functions.


def to_dict(obj: tuple) -> dict:
    """
    Generate a dict representation of a NamedTuple instance.

    This just uses the built-in ``_asdict`` method on the intance, but also
    calls this on any child NamedTuple instances (recursively) so that the
    entire tree is cast to ``dict``.

    Parameters
    ----------
    obj : tuple
        A NamedTuple instance.

    Returns
    -------
    dict

    """
    if not hasattr(obj, '_asdict'):  # NamedTuple-generated classes have this.
        return {}
    data = obj._asdict()  # type: ignore
    _data = {}

    def _cast(obj: Any) -> Any:
        if hasattr(obj, '_asdict'):
            obj = to_dict(obj)
        elif isinstance(obj, datetime):
            obj = obj.isoformat()
        elif isinstance(obj, list):
            obj = [_cast(o) for o in obj]
        return obj

    for key, value in data.items():

        _data[key] = _cast(value)
    return _data


def from_dict(cls: type, data: dict) -> Any:
    """
    Generate a NamedTuple instance from a dict, with recursion.

    This is the inverse of :func:`to_dict`.

    It's easy to instantiate NamedTuples from dicts, but it's not so easy if
    a NamedTuple field is typed with another NamedTuple. This function
    instantiates a NamedTuple class ``cls`` with the data in dict ``data``,
    and also instantiates any referenced NamedTuple classes expected by
    ``cls``'s fields with the appropriate data in ``data``.

    Parameters
    ----------
    cls: type
        Any NamedTuple class.

    data: dict
        Data with which to instantiate ``cls`` and its children.

    Returns
    -------
    NamedTuple
        An instance of ``cls``.
    """
    _data = {}
    for field, field_type in cls._field_types.items():  # type: ignore
        if field not in data:
            continue
        value = data[field]
        target_type = _get_cast_type(field_type, value)
        if target_type:
            value = target_type(value)
        _data[field] = value
    if hasattr(cls, 'before_init'):
        cls.before_init(_data)
    return cls(**_data)


def _is_a_namedtuple(field_type: type) -> bool:
    """Determine whether or not a field type is a NamedTuple class."""
    return hasattr(field_type, '_fields')


def _is_typing_type(field_type: type) -> bool:
    """Determine whether a type is a typing class."""
    return hasattr(field_type, '_subs_tree')


def _is_nested_type(field_type: type) -> bool:
    """Determine whether a typing class is nested (e.g. Union[str, int])."""
    return type(field_type._subs_tree()) is tuple  # type: ignore


def _get_cast_type_for_str(field_type: type) -> Optional[Callable]:
    """
    Determine the target type for a ``str`` value.

    Returns ``None`` if a suitable target cannot be determined.
    """
    if (field_type is datetime or
        (_is_typing_type(field_type) and
         _is_nested_type(field_type) and
         datetime in field_type._subs_tree())):  # type: ignore
        return dateutil.parser.parse
    return None


def _get_cast_type_for_dict(field_type: type) -> Optional[Callable]:
    """
    Determine the NamedTuple target type for a ``dict`` value.

    Returns ``None`` if a suitable target cannot be determined.
    """
    # Is the expected type for the field a NamedTuple class?
    if _is_a_namedtuple(field_type):
        return partial(from_dict, field_type)

    # Is the expected type a nested Type? There may be a NamedTuple hiding
    # in there...
    if _is_typing_type(field_type) and _is_nested_type(field_type):

        # Look for either a NamedTuple class, or dict type.
        for s_type in field_type._subs_tree():  # type: ignore
            if s_type is dict:
                return None    # We already have one of these, nothing to do.
            if _is_a_namedtuple(s_type):
                return partial(from_dict, s_type)
    return None


# Recursive coersion on anything more complicated than these simple cases is
# pretty hard. It's easier to implement anything else (e.g. a List of
# something type-ish) on the domain class itself.
def _get_cast_type(field_type: type, value: Any) -> Optional[Callable]:
    """Get a casting callable for a field type/value."""
    if type(value) is dict:
        return _get_cast_type_for_dict(field_type)
    if type(value) is str:
        return _get_cast_type_for_str(field_type)
    return None
