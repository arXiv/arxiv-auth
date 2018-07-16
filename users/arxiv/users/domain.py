"""Defines user concepts for use in arXiv-NG services."""

from typing import Any, Optional, Type, NamedTuple, List, Callable
from datetime import datetime
import dateutil.parser
from pytz import timezone
from functools import partial
from arxiv import taxonomy

from arxiv.base import logging

logger = logging.getLogger(__name__)
EASTERN = timezone('US/Eastern')


class Category(NamedTuple):
    """Reprents a classification category."""

    archive: str
    """Archives group together related subjects in a domain."""

    subject: Optional[str] = None
    """Leaf-level classification in the arXiv taxonomy."""

    @classmethod
    def from_compound(cls, category: str) -> 'Category':
        """
        Create a :class:`.Category` from a compound classification slug.

        E.g. "astro-ph.CO" -> Category(archive="astro-ph", subject="CO")

        Parameters
        ----------
        category : str
            A dot-delimited compound category slug.

        Returns
        -------
        :class:`.Category`

        """
        parts = category.split('.')
        if len(parts) == 2:
            return cls(*parts)
        return cls(category, '')

    @property
    def compound(self) -> str:
        """Compound category name."""
        if self.subject:
            return f"{self.archive}.{self.subject}"
        return self.archive

    @property
    def display(self) -> str:
        """Display name for this category."""
        name: str = taxonomy.CATEGORIES[self.compound]['name']
        return name


class Client(NamedTuple):
    """Placeholder for API client."""

    client_id: str
    """Unique identifier for a :class:`.Client`."""


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

    Items should be one of :ref:`arxiv.taxonomy.GROUPS`.
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
        return self.default_category.archive

    @property
    def default_subject(self) -> Optional[str]:
        """The subject of the default category."""
        return self.default_category.subject

    @property
    def groups_display(self) -> str:
        """Display-ready representation of active groups for this profile."""
        return ", ".join([
            taxonomy.GROUPS[group]['name'] for group in self.submission_groups
        ])


class Authorizations(NamedTuple):
    """Authorization information, e.g. associated with a :class:`.Session`."""

    classic: int = 0
    """Capability code associated with a user's session."""

    endorsements: List[Category] = []
    """Categories to which the user is permitted to submit."""

    scopes: list = []
    """Authorized scopes. See :mod:`arxiv.users.auth.scopes`."""

    @classmethod
    def before_init(cls, data: dict) -> None:
        """Make sure that endorsements are :class:`.Category` instances."""
        # Iterative coercion is hard. It's a lot easier to handle this here
        # than to implement a general-purpose coercsion.
        # if self.endorsements and type(self.endorsements[0]) is not Category:
        data['endorsements'] = [
            Category(*obj) for obj in data.get('endorsements', [])
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

    @property
    def expired(self) -> bool:
        """Expired if the current time is later than :attr:`.end_time`."""
        return bool(self.end_time is not None
                    and datetime.now(tz=EASTERN) >= self.end_time)

    @property
    def expires(self) -> Optional[int]:
        """
        Number of seconds until the session expires.

        If the session is already expired, returns 0.
        """
        if self.end_time is None:
            return None
        return max((self.end_time - datetime.now(tz=EASTERN)).seconds, 0)

    # Consider for later:
    #  localization (preferred language)
    #  preferences for sharing contact info


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
    for key, value in data.items():
        if hasattr(value, '_asdict'):
            value = to_dict(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        _data[key] = value
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
