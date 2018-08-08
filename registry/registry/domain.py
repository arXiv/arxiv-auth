"""
Core domain classes for the API client registry.

See also :mod:`arxiv.users.domain`.
"""

from datetime import datetime
from typing import NamedTuple, Optional, List
from arxiv.users.domain import Session, Client, User, Authorizations


class ClientCredential(NamedTuple):
    """Key-pair for API client authentication."""

    client_id: str
    """Public identifier for the API client."""

    client_secret: str
    """Secret key for API client authentication."""


class ClientAuthorization(NamedTuple):
    """A specific authorization for a :class:`Client`."""

    client_id: str
    """The client to which this authorization applies."""

    scope: str
    """The specific scope being granted."""

    requested: datetime
    """The date/time when the scope was requsted."""

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

    client_id: str
    """The client to which this authorization applies."""

    grant_type: str
    """Must be one of :attr:`.GRANT_TYPES`."""

    requested: datetime
    """The date/time when the grant type was requsted."""

    authorized: Optional[datetime] = None
    """The date/time when the grant type was authorized."""
