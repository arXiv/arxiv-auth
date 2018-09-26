"""
Core domain classes for the API client registry.

See also :mod:`arxiv.users.domain`.
"""

from datetime import datetime
from typing import NamedTuple, Optional, List
from arxiv.users.domain import Session, Client, User, Authorizations, User, \
    Scope, Category


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


class AuthorizationCode(NamedTuple):
    """An authorization code granted by a user to an API client."""

    user_id: str
    """The unique identifier of the arXiv user granting the authorization."""

    username: str
    """The username of the arXiv user granting the authorization."""

    user_email: str
    """The email address of the arXiv user granting the authorization."""

    client_id: str
    """The unique identifier of the API client."""

    redirect_uri: str
    """The URI to which the user should be redirected."""

    scope: str
    """The scope authorized by the user."""

    code: str
    """The authorization code itself."""

    created: datetime
    """The time when the auth code was generated."""

    expires: datetime
    """The time when the auth code expires."""
