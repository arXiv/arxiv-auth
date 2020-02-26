"""
OAuth2 (RFC6749) implementation, using :mod:`authlib`.

This module extends the :mod:`authlib.flask` implementation, leveraging client
data stored in :mod:`registry.services.datastore` and instantiating authorized
sessions in :mod:`registry.services.sessions`.

The current implementation supports the `client_credentials` and
`authorization_code` grants.

.. todo:: Implement backend & integration to control client endorsements.


"""

from typing import List, Optional, Any
import hashlib
from datetime import timedelta, datetime
from flask import Flask, request
from authlib.flask.oauth2 import AuthorizationServer
from authlib.oauth2.rfc6749 import ClientMixin, grants, OAuth2Request, \
    OAuth2Error
from authlib.oauth2.rfc6749.util import list_to_scope
from authlib.common.security import generate_token

from arxiv.base import logging
from ..services import datastore, SessionStore
from .. import domain

logger = logging.getLogger(__name__)


class OAuth2User(object):
    """
    Represents the resource owner in OAuth2 workflows.

    This is a thin wrapper around :class:`domain.User` to support Authlib
    integration.
    """

    def __init__(self, user: domain.User) -> None:
        """Initialize with a :class:`domain.User`."""
        self._user = user

    def get_user_id(self) -> str:
        """Get the ID of the user."""
        return self._user.user_id

    def get_user_email(self) -> str:
        """Get the email address of the user."""
        return self._user.email

    def get_username(self) -> str:
        """Get the username of the user."""
        return self._user.username


class OAuth2AuthorizationCode(object):
    """Wraps :class:`domain.AuthorizationCode` for use in OAuth2 workflows."""

    _fields = ['user_id', 'username', 'user_email', 'client_id',
               'redirect_uri', 'scope', 'code', 'created', 'expires']

    def __init__(self, auth_code: domain.AuthorizationCode) -> None:
        """Initialize with the wrapped :class:`domain.AuthorizationCode`."""
        self._code = auth_code

    def __getattr__(self, key: str) -> Any:
        """Get an attribute from the wrapped :class:`.AuthorizationCode`."""
        if key in self._fields:
            return getattr(self._code, key)
        raise AttributeError(f'No attribute {key}')

    def is_expired(self) -> bool:
        """Indicate whether the code is expired."""
        return self._code.expires <= datetime.now()

    def get_redirect_uri(self) -> str:
        """Get the authorization code's redirect URI."""
        return self._code.redirect_uri

    def get_scope(self) -> str:
        """Get the scope for the authorization code."""
        return self._code.scope


class OAuth2Client(ClientMixin):
    """
    Implementation of an OAuth2 client as described in RFC6749.

    This class essentially wraps an aggregate of registry domain objects for a
    particular client, and implements methods expected by the
    :class:`AuthorizationServer`.
    """

    def __init__(self, client: domain.Client,
                 credential: domain.ClientCredential,
                 authorizations: List[domain.ClientAuthorization],
                 grant_types: List[domain.ClientGrantType]) -> None:
        """Initialize with domain data about a client."""
        logger.debug('New OAuth2Client with client_id %s', client.client_id)
        self._client = client
        self._credential = credential
        self._scopes = set([str(auth.scope) for auth in authorizations])
        self._grant_types = [gtype.grant_type for gtype in grant_types]

    @property
    def name(self) -> str:
        """Get the client name."""
        return self._client.name

    @property
    def description(self) -> str:
        """Get the client description."""
        return self._client.description

    @property
    def scopes(self) -> List[str]:
        """Return authorized scopes as a list."""
        return list(self._scopes)

    @property
    def url(self) -> str:
        """Get the client URL."""
        return self._client.url

    @property
    def client_id(self) -> str:
        """Get the client ID."""
        return self._client.client_id

    def get_allowed_scope(self, scope: str) -> str:
        """Get list of scopes supported by client as string."""
        logger.debug('Get allowed scope: %s in %s',
                     scope, list_to_scope(self.scopes))
        if not scope:
            return ''
        allowed = set(self.scopes)
        l_allowed = list_to_scope([sc for sc in scope.split() if sc in allowed])
        logger.debug('Allowed scope: %s', l_allowed)
        return l_allowed

    def check_client_secret(self, client_secret: str) -> bool:
        """Check that the provided client secret is correct."""
        logger.debug('Check client secret %s', client_secret)
        hashed = hashlib.sha256(client_secret.encode('utf-8')).hexdigest()
        return self._credential.client_secret == hashed

    def check_grant_type(self, grant_type: str) -> bool:
        """Check that the client is authorized for the proposed grant type."""
        logger.debug('Check grant type %s', grant_type)
        return grant_type in self._grant_types

    def check_redirect_uri(self, redirect_uri: str) -> bool:
        """Check that the provided redirect URI is authorized."""
        logger.debug('Check redirect URI: %s, %s',
                     redirect_uri, self._client.redirect_uri)
        return redirect_uri == self._client.redirect_uri

    def check_requested_scopes(self, scopes: set) -> bool:
        """Check that the requested scopes are authorized for this client."""
        # If there is an active user on the session, ensure that we are not
        # granting scopes for which the user themself is not authorized.
        logger.debug('Client requests scopes: %s', scopes)

        if request.auth and request.auth.user:
            session_scopes = {
                str(s) for s in request.auth.authorizations.scopes
            }
            logger.debug('Authorized scopes on user session: %s',
                         session_scopes)
            return self._scopes.issuperset(scopes) and \
                session_scopes.issuperset(scopes)
        return self._scopes.issuperset(scopes)

    def check_response_type(self, response_type: str) -> bool:
        """Check the proposed response type."""
        logger.debug('Check response type: %s', response_type)
        return response_type == 'code'

    def check_token_endpoint_auth_method(self, method: str) -> bool:
        """Force POST auth method."""
        logger.debug('Check endpoint auth method: %s', method)
        return method == 'client_secret_post'

    def get_default_redirect_uri(self) -> str:
        """Get the default redirect URI for the client."""
        return self._client.redirect_uri

    def has_client_secret(self) -> bool:
        """Check that the client has a secret."""
        logger.debug('Check has client secret')
        return self._credential.client_secret is not None


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    """Authorization code grant for arXiv users."""

    EXPIRES = 3600
    TOKEN_ENDPOINT_AUTH_METHODS = ['client_secret_post']

    def create_authorization_code(self, client: OAuth2Client,
                                  grant_user: OAuth2User,
                                  request: OAuth2Request) -> str:
        """
        Generate and store a new authorization code.

        Parameters
        ----------
        client : :class:`OAuth2Client`
            The client requesting authorization.
        grant_user : :class:`OAuth2User`
            The resource owner who has granted authorization to the client.
        request : :class:`OAuth2Request`
            The request wrapper containing request details.

        Returns
        -------
        str
            An authorization code that the client can exchange for an access
            token.

        """
        code = generate_token(48)
        created = datetime.now()
        datastore.save_auth_code(domain.AuthorizationCode(
            code=code,
            user_id=grant_user.get_user_id(),
            username=grant_user.get_username(),
            user_email=grant_user.get_user_email(),
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            client_id=client.client_id,
            created=created,
            expires=created + timedelta(seconds=self.EXPIRES)

        ))
        return code

    def parse_authorization_code(self, code: str, client: OAuth2Client) \
            -> Optional[domain.AuthorizationCode]:
        """Attempt to retrieve an auth code for an API client."""
        logger.debug('Parse authorization code %s for %s', code, client)
        try:
            code_grant = OAuth2AuthorizationCode(
                datastore.load_auth_code(code, client.client_id)
            )
        except datastore.NoSuchAuthCode:
            logger.debug(f'No such auth code: {code}')
            return

        if code_grant.is_expired():
            return
        return code_grant

    def delete_authorization_code(self, auth_code: OAuth2AuthorizationCode) \
            -> None:
        """Delete an auth code."""
        datastore.delete_auth_code(auth_code.code, auth_code.client_id)

    def authenticate_user(self, auth_code: OAuth2AuthorizationCode) \
            -> OAuth2User:
        """Authenticate the user implicated in the auth code."""
        code_grant = OAuth2AuthorizationCode(
            datastore.load_auth_code_by_user(auth_code.code, auth_code.user_id)
        )
        return OAuth2User(domain.User(
            user_id=code_grant.user_id,
            email=code_grant.user_email,
            username=code_grant.username
        ))


class ClientCredentialsGrant(grants.ClientCredentialsGrant):
    """Our client credentials grant supports only POST requests."""

    TOKEN_ENDPOINT_AUTH_METHODS = ['client_secret_post']


def get_client(client_id: str) -> Optional[OAuth2Client]:
    """
    Load client data and generate a :class:`OAuth2Client`.

    Parameters
    ----------
    client_id : str

    Returns
    -------
    :class:`OAuth2Client` or None
        If the client is not found, returns `None`.

    """
    logger.debug('Get client with ID %s', client_id)
    try:
        client = OAuth2Client(*datastore.load_client(client_id))
        logger.debug('Got client %s', client_id)
    except datastore.NoSuchClient as e:
        logger.debug('No such client %s: %s', client_id, e)
        return None
    return client


def save_token(token: dict, oauth_request: OAuth2Request) -> None:
    """
    Persist an auth token as a :class:`domain.Session`.

    We use the access token as the session ID. This makes for a fast lookup
    by the :mod:`authenticator` service.

    Parameters
    ----------
    token : dict
        Token data generated by the OAuth2 :class:`AuthorizationServer`.
        At this point the token has not been stored.
    oauth_request : :class:`OAuth2Request`
        Wrapper for OAuth2-related request data.

    """
    logger.debug("Persist token: %s", token)
    session_id = token['access_token']
    client = oauth_request.client
    logger.debug("Client has scopes %s", client.scopes)
    user = oauth_request.user._user if oauth_request.user else None
    authorizations = domain.Authorizations(
        scopes=client.scopes,
        endorsements=get_endorsements(client)
    )
    sessions = SessionStore.current_session()
    session = sessions.create(authorizations, request.remote_addr,
                              request.remote_addr, user=user,
                              client=client._client, session_id=session_id)
    logger.debug('Created session %s', session.session_id)


def get_endorsements(client: domain.Client) -> List[domain.Category]:
    """
    Get endorsed categories for a client.

    The current implementation just returns all categories.

    Parameters
    ----------
    client : :class:`domain.Client`

    Returns
    -------
    list
        Each item is a :class:`domain.Category`.

    """
    return [domain.Category('*')]


def create_server() -> AuthorizationServer:
    """Instantiate and configure an :class:`AuthorizationServer`."""
    server = AuthorizationServer(query_client=get_client,
                                 save_token=save_token)
    server.register_grant(ClientCredentialsGrant)
    server.register_grant(AuthorizationCodeGrant)
    logger.debug('Created server %s', id(server))
    return server


def init_app(app: Flask) -> None:
    """Attach an :class:`AuthorizationServer` to a :class:`Flask` app."""
    server = create_server()
    server.init_app(app)
    app.server = server
