"""Provides a session store."""

import json
import time
import uuid
import random
from datetime import datetime

from typing import Any, Optional, Union, Tuple

from functools import wraps
import redis
import jwt

from ... import domain
from ..exceptions import SessionCreationFailed, InvalidToken, \
    SessionDeletionFailed, SessionUnknown

from arxiv.base.globals import get_application_config, get_application_global
from arxiv.base import logging

logger = logging.getLogger(__name__)


def _generate_nonce(length: int = 8) -> str:
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def _now() -> int:
    epoch = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
    return int(round(epoch))


class SessionStore(object):
    """
    Manages a connection to Redis.

    In reality, the StrictRedis instance is thread safe, and connections are
    attached at the time a command is executed. This class simply provides a
    container for configuration.
    """

    def __init__(self, host: str, port: int, db: int, secret: str) -> None:
        """Open the connection to Redis."""
        self.r = redis.StrictRedis(host=host, port=port, db=db)
        self._secret = secret

    def create(self, user: domain.User, authorizations: domain.Authorizations,
               ip_address: str, remote_host: str, tracking_cookie: str = '') \
            -> Tuple[domain.Session, str]:
        """
        Create a new session.

        Parameters
        ----------
        user : :class:`domain.User`
        authorizations : :class:`domain.Authorizations`

        Returns
        -------
        :class:`.Session`
        """
        session_id = str(uuid.uuid4())
        start_time = _now()
        session = domain.Session(
            session_id=session_id,
            user=user,
            start_time=start_time,
            authorizations=authorizations,
            nonce=_generate_nonce()
        )
        cookie = self._pack_cookie({
            'user_id': user.user_id,
            'session_id': session_id,
            'nonce': session.nonce
        })

        try:
            self.r.set(session_id, json.dumps(domain.to_dict(session)))
        except redis.exceptions.ConnectionError as e:
            raise SessionCreationFailed(f'Connection failed: {e}') from e
        except Exception as e:
            raise SessionCreationFailed(f'Failed to create: {e}') from e

        return session, cookie

    def delete(self, session_id: str) -> None:
        """
        Delete a session in the key-value store.

        Parameters
        ----------
        session_id : str
        """
        try:
            self.r.delete(session_id)
        except redis.exceptions.ConnectionError as e:
            raise SessionDeletionFailed(f'Connection failed: {e}') from e
        except Exception as e:
            raise SessionDeletionFailed(f'Failed to delete: {e}') from e

    def invalidate(self, cookie: str) -> None:
        """
        Invalidate a session in the key-value store.

        Parameters
        ----------
        session_id : str
        """
        try:
            cookie_data = self._unpack_cookie(cookie)
        except jwt.exceptions.DecodeError as e:
            raise SessionDeletionFailed('Bad session token') from e
        try:
            session_data = self.load(cookie_data['session_id'])
            if session_data.nonce != cookie_data['nonce'] \
                    or session_data.user_id != cookie_data['user_id']:
                raise SessionDeletionFailed('Bad session token')
            session_data.end_time = _now()
            data = json.dumps(domain.to_dict(session_data))
            self.r.set(cookie_data['session_id'], data)
        except redis.exceptions.ConnectionError as e:
            raise SessionDeletionFailed(f'Connection failed: {e}') from e
        except Exception as e:
            raise SessionDeletionFailed(f'Failed to delete: {e}') from e

    def load(self, cookie: str) -> domain.Session:
        """Load a session using a session cookie."""
        try:
            cookie_data = self._unpack_cookie(cookie)
            session_id = cookie_data['session_id']
            user_id = cookie_data.get('user_id')
            client_id = cookie_data.get('client_id')
            nonce = cookie_data['nonce']
        except (KeyError, jwt.exceptions.DecodeError) as e:
            raise InvalidToken('Token payload malformed') from e

        session = self._load(session_id)
        if session.expired:
            raise InvalidToken('Session has expired')
        if nonce != session.nonce:
            raise InvalidToken('Invalid token; likely a forgery')
        if user_id and user_id != session.user.user_id:
            raise InvalidToken('Invalid token; likely a forgery')
        if client_id and client_id != session.client.client_id:
            raise InvalidToken('Invalid token; likely a forgery')
        return session

    def _load(self, session_id: str) -> domain.Session:
        """Get session data by session ID."""
        user_session: Union[str, bytes, bytearray] = self.r.get(session_id)
        if not user_session:
            logger.error(f'No such session: {session_id}')
            raise SessionUnknown(f'Failed to find session {session_id}')
        try:
            data: dict = json.loads(user_session)
        except json.decoder.JSONDecodeError:
            raise InvalidToken('Invalid or corrupted session token')
        return domain.from_dict(domain.Session, data)

    def _unpack_cookie(self, cookie: str) -> dict:
        return jwt.decode(cookie, self._secret)

    def _pack_cookie(self, cookie_data: dict) -> str:
        return jwt.encode(cookie_data, self._secret)


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('REDIS_HOST', 'localhost')
    config.setdefault('REDIS_PORT', '6379')
    config.setdefault('REDIS_DATABASE', '0')
    config.setdefault('JWT_SECRET', 'foosecret')


def get_redis_session(app: object = None) -> SessionStore:
    """Get a new session with the search index."""
    config = get_application_config(app)
    host = config.get('REDIS_HOST', 'localhost')
    port = int(config.get('REDIS_PORT', '6379'))
    db = int(config.get('REDIS_DATABASE', '0'))
    secret = config['JWT_SECRET']
    return SessionStore(host, port, db, secret)


def current_session() -> SessionStore:
    """Get/create :class:`.SearchSession` for this context."""
    g = get_application_global()
    if not g:
        return get_redis_session()
    if 'redis' not in g:
        g.redis = get_redis_session()
    return g.redis      # type: ignore


@wraps(SessionStore.create)
def create(user: domain.User, authorizations: domain.Authorizations,
           ip_address: str, remote_host: str, tracking_cookie: str = '') \
        -> domain.Session:
    """
    Create a new session.

    Parameters
    ----------
    user : :class:`domain.User`
    authorizations : :class:`domain.Authorizations`

    Returns
    -------
    :class:`.Session`
    """
    return current_session().create(user, authorizations, ip_address,
                                    remote_host, tracking_cookie)


@wraps(SessionStore.load)
def load(session_id: str) -> dict:
    """
    Invalidate a session in the key-value store.

    Parameters
    ----------
    session_id : str

    Returns
    -------
    dict
    """
    return current_session().load(session_id)


@wraps(SessionStore.delete)
def delete(session_id: str) -> None:
    """
    Delete a session in the key-value store.

    Parameters
    ----------
    session_id : str
    """
    return current_session().delete(session_id)


@wraps(SessionStore.invalidate)
def invalidate(session_id: str) -> None:
    """
    Invalidates a session in the key-value store.

    Parameters
    ----------
    session_id : str
    """
    return current_session().invalidate(session_id)
