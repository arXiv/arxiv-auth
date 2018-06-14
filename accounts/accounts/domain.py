"""Defines the core data structures for the arxiv-accounts service."""

from typing import Any, Optional, Type, NamedTuple, List
from datetime import datetime
from arxiv import taxonomy
import pycountry


class UserProfile(NamedTuple):
    """User profile data."""

    STAFF = ('1', 'Staff')
    PROFESSOR = ('2', 'Professor')
    POST_DOC = ('3', 'Post doc')
    GRAD_STUDENT = ('4', 'Grad student')
    OTHER = ('5', 'Other')
    RANKS = [STAFF, PROFESSOR, POST_DOC, GRAD_STUDENT, OTHER]

    COUNTRIES = [(country.alpha_2, country.name)
                 for country in pycountry.countries]
    """ISO 3166 countries, identified by their alpha-2 code."""

    GROUPS = [
        (key, group['name']) for key, group in taxonomy.GROUPS.items()
        if not group.get('is_test', False)
    ]
    """High-level classification groups."""

    CATEGORIES = [
        (archive['name'], [
            (category_id, category['name'])
            for category_id, category in taxonomy.CATEGORIES.items()
            if category['is_active'] and category['in_archive'] == archive_id
        ])
        for archive_id, archive in taxonomy.ARCHIVES.items()
        if 'end_date' not in archive
    ]
    """Categories grouped by archive."""

    organization: str
    """Institutional affiliation."""

    country: str
    """Should be one of :prop:`.COUNTRIES`."""

    rank: int
    """Academic rank. Must be one of :prop:`.RANKS`."""

    submission_groups: List[str]
    """
    Groups to which the user prefers to submit.

    Items should be one of :prop:`.GROUPS`.
    """

    default_category: str
    """Default submission category. Should be one of :prop:`.CATEGORIES`."""

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


class UserPrivileges(NamedTuple):
    classic: int    # pylint: disable=E701
    endorsement_domains: list = []
    scopes: list = []


class UserFullName(NamedTuple):

    forename: str
    surname: str
    suffix: str = ''


class User(NamedTuple):
    """Represents an arXiv user and their privileges."""

    user_id: str
    username: str
    email: str
    privileges: UserPrivileges

    name: Optional[UserFullName] = None


class UserRegistration(NamedTuple):
    """Represents a request to register a new user."""

    username: str
    password: str
    email: str
    name: UserFullName
    profile: UserProfile


class UserSession(NamedTuple):
    session_id: str
    cookie: bytes
    """Session cookie payload."""
    user: User
    start_time: int
    end_time: int = 0
    scopes: List[str] = []

    @property
    def expired(self) -> bool:
        """Expired if the current time is later than :prop:`.end_time`."""
        now = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
        return bool(self.end_time and now >= self.end_time)
    # Consider for later:
    #  localization (preferred language)
    #  preferences for sharing contact info
