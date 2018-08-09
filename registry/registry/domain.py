"""
Core domain classes for the API client registry.

See also :mod:`arxiv.users.domain`.
"""

from datetime import datetime
from typing import NamedTuple, Optional, List
from arxiv.users.domain import Session, Client, User, Authorizations


class ClientCredential(NamedTuple):
    """Key-pair for API client authentication."""

    client_secret: str
    """Hashed secret key for API client authentication."""

    client_id: Optional[str] = None
    """Public identifier for the API client."""


class ClientAuthorization(NamedTuple):
    """A specific authorization for a :class:`Client`."""

    scope: str
    """The specific scope being granted."""

    requested: datetime
    """The date/time when the scope was requsted."""

    authorization_id: Optional[str] = None
    """Unique identifier for the scope authorization."""

    client_id: Optional[str] = None
    """The client to which this authorization applies."""

    authorized: Optional[datetime] = None
    """The date/time when the scope was authorized."""


class ClientGrantType(NamedTuple):
    """A grant type for which a client is authorized."""

    AUTHORIZATION_CODE = 'authorization_code'
    IMPLICIT = 'implicit'
    CLIENT_CREDENTIALS = 'client_credentials'
    PASSWORD = 'password'
    GRANT_TYPES = (
        AUTHORIZATION_CODE,
        IMPLICIT,
        CLIENT_CREDENTIALS,
        PASSWORD
    )

    grant_type: str
    """Must be one of :attr:`.GRANT_TYPES`."""

    requested: datetime
    """The date/time when the grant type was requsted."""

    grant_type_id: Optional[str] = None
    """Unique identifier for grant type authorization."""

    client_id: Optional[str] = None
    """The client to which this authorization applies."""

    authorized: Optional[datetime] = None
    """The date/time when the grant type was authorized."""
