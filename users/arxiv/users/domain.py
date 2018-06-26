"""Defines user concepts for use in arXiv-NG services."""

from typing import Any, Optional, Type, NamedTuple, List
from datetime import datetime
import dateutil.parser
from arxiv import taxonomy


def to_dict(obj: tuple) -> dict:
    """Generate a dict representation of a NamedTuple instance."""
    data = obj._asdict()
    _data = {}
    for key, value in data.items():
        if hasattr(value, '_asdict'):
            value = to_dict(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        _data[key] = value
    return _data


def from_dict(cls, data: dict) -> NamedTuple:
    """Generate a NamedTuple instance from a dict."""
    _data = {}
    for field, field_type in cls._field_types.items():
        if field not in data:
            continue
        value = data[field]
        if type(value) is dict:
            if hasattr(field_type, '_fields'):
                value = from_dict(field_type, value)
            elif hasattr(field_type, '_subs_tree'):
                for s_type in field_type._subs_tree():
                    if s_type is dict:
                        break
                    if hasattr(s_type, '_fields'):
                        value = from_dict(s_type, value)
                        break
        elif (field_type is datetime or
              (hasattr(field_type, '_subs_tree') and
               datetime in field_type._subs_tree())):
            value = dateutil.parser.parse(value)
        _data[field] = value
    return cls(**_data)


class Category(NamedTuple):
    archive: str
    subject: Optional[str] = None


class Client(NamedTuple):
    """Placeholder for API client."""
    client_id: str


class UserProfile(NamedTuple):
    """User profile data."""

    STAFF = ('1', 'Staff')
    PROFESSOR = ('2', 'Professor')
    POST_DOC = ('3', 'Post doc')
    GRAD_STUDENT = ('4', 'Grad student')
    OTHER = ('5', 'Other')
    RANKS = [STAFF, PROFESSOR, POST_DOC, GRAD_STUDENT, OTHER]

    organization: str
    """Institutional affiliation."""

    country: str
    """Should be one of :prop:`.COUNTRIES`."""

    rank: int
    """Academic rank. Must be one of :prop:`.RANKS`."""

    submission_groups: List[str]
    """
    Groups to which the user prefers to submit.

    Items should be one of :ref:`arxiv.taxonomy.GROUPS`.
    """

    default_category: Category
    """
    Default submission category.

    Should be one of :ref:`.arxiv.taxonomy.CATEGORIES`.
    """

    homepage_url: str = ''
    """User's homepage or external profile URL."""

    remember_me: bool = True
    """Indicates whether the user prefers permanent session cookies."""

    @property
    def default_archive(self) -> str:
        """The archive of the default category."""
        return self.default_category.split('.')[0]

    @property
    def default_subject(self) -> Optional[str]:
        """The subject of the default category."""
        parts = self.default_category.split('.')
        if len(parts) < 2:
            return None
        return parts[-1]


class Authorizations(NamedTuple):
    classic: int = 0
    endorsements: List[Category] = []
    scopes: list = []


class UserFullName(NamedTuple):
    forename: str
    surname: str
    suffix: str = ''


class User(NamedTuple):
    """Represents an arXiv user and their authorizations."""

    user_id: str
    username: str
    email: str

    name: Optional[UserFullName] = None


class Session(NamedTuple):
    """Represents an authenticated session in the arXiv system."""
    session_id: str
    """Session cookie payload."""
    start_time: datetime
    user: Optional[User] = None
    client: Optional[Client] = None
    end_time: Optional[datetime] = None
    authorizations: Optional[Authorizations] = None
    ip_address: Optional[str] = None
    remote_host: Optional[str] = None
    nonce: Optional[str] = None

    @property
    def expired(self) -> bool:
        """Expired if the current time is later than :prop:`.end_time`."""
        return bool(self.end_time and datetime.now() >= self.end_time)

    # Consider for later:
    #  localization (preferred language)
    #  preferences for sharing contact info


class UserRegistration(NamedTuple):
    """Represents a request to register a new user."""

    username: str
    password: str
    email: str
    name: UserFullName
    profile: UserProfile
