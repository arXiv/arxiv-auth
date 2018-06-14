"""Provides a session_store session store."""

import json
import time
import uuid
import random
from datetime import datetime

from typing import Any, Optional, Union

from functools import wraps
import redis
import jwt

from accounts.domain import User, UserSession
from accounts.services.exceptions import SessionCreationFailed, \
    SessionDeletionFailed, UserSessionUnknown
from arxiv.base.globals import get_application_config, get_application_global
from arxiv.base import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _generate_nonce(length: int = 8) -> str:
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def _now() -> int:
    epoch = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
    return int(round(epoch))


class RedisSession(object):
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

    def create_user_session(self, user: User, ip_address: str,
                            remote_host: str, tracking_cookie: str = '') \
            -> UserSession:
        """
        Create a new session.

        Parameters
        ----------
        user : :class:`.User`

        Returns
        -------
        :class:`.UserSession`
        """
        session_id = str(uuid.uuid4())
        nonce = _generate_nonce()
        start_time = _now()
        data = json.dumps({
            'user_id': user.user_id,
            'username': user.username,
            'user_email': user.email,

            'start_time': start_time,
            'end_time': None,
            'ip_address': ip_address,
            'remote_host': remote_host,

            'scopes': user.privileges.scopes,
            'domains': user.privileges.endorsement_domains,
            'nonce': nonce
        })

        cookie = self._pack_cookie({
            'user_id': user.user_id,
            'session_id': session_id,
            'nonce': nonce
        })

        try:
            self.r.set(session_id, data)
        except redis.exceptions.ConnectionError as e:
            raise SessionCreationFailed(f'Connection failed: {e}') from e
        except Exception as e:
            raise SessionCreationFailed(f'Failed to create: {e}') from e
        return UserSession(
            session_id=session_id,
            cookie=cookie,
            user=user,
            start_time=start_time
        )

    def delete_user_session(self, session_id: str) -> None:
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

    def invalidate_user_session(self, session_cookie: str) -> None:
        """
        Invalidate a session in the key-value store.

        Parameters
        ----------
        session_id : str
        """
        try:
            cookie_data = self._unpack_cookie(session_cookie)
        except jwt.exceptions.DecodeError as e:
            raise SessionDeletionFailed('Bad session token') from e
        try:
            session_data = self.get_user_session(cookie_data['session_id'])
            if session_data['nonce'] != cookie_data['nonce'] \
                    or session_data['user_id'] != cookie_data['user_id']:
                raise SessionDeletionFailed('Bad session token')
            session_data['end_time'] = _now()
            data = json.dumps(session_data)
            self.r.set(cookie_data['session_id'], data)
        except redis.exceptions.ConnectionError as e:
            raise SessionDeletionFailed(f'Connection failed: {e}') from e
        except Exception as e:
            raise SessionDeletionFailed(f'Failed to delete: {e}') from e

    def get_user_session(self, session_id: str) -> dict:
        """Get Session from session id."""
        user_session: Union[str, bytes, bytearray] = self.r.get(session_id)
        if not user_session:
            logger.error(f'No such session: {session_id}')
            raise UserSessionUnknown(f'Failed to find session {id}')
        data: dict = json.loads(user_session)
        return data

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


def get_redis_session(app: object = None) -> RedisSession:
    """Get a new session with the search index."""
    config = get_application_config(app)
    host = config.get('REDIS_HOST', 'localhost')
    port = int(config.get('REDIS_PORT', '6379'))
    db = int(config.get('REDIS_DATABASE', '0'))
    secret = config['JWT_SECRET']
    return RedisSession(host, port, db, secret)


def current_session() -> RedisSession:
    """Get/create :class:`.SearchSession` for this context."""
    g = get_application_global()
    if not g:
        return get_redis_session()
    if 'redis' not in g:
        g.redis = get_redis_session()
    return g.redis      # type: ignore


@wraps(RedisSession.create_user_session)
def create_user_session(user: User, ip_address: str, remote_host: str,
                        tracking_cookie: str = '') -> UserSession:
    """
    Create a new session.

    Parameters
    ----------
    user : :class:`.User`

    Returns
    -------
    :class:`.UserSession`
    """
    return current_session().create_user_session(user, ip_address, remote_host,
                                                 tracking_cookie)


@wraps(RedisSession.get_user_session)
def get_user_session(session_id: str) -> dict:
    """
    Invalidate a session in the key-value store.

    Parameters
    ----------
    session_id : str

    Returns
    -------
    dict
    """
    return current_session().get_user_session(session_id)


@wraps(RedisSession.delete_user_session)
def delete_user_session(session_id: str) -> None:
    """
    Delete a session in the key-value store.

    Parameters
    ----------
    session_id : str
    """
    return current_session().delete_user_session(session_id)


@wraps(RedisSession.invalidate_user_session)
def invalidate_user_session(session_id: str) -> None:
    """
    Invalidates a session in the key-value store.

    Parameters
    ----------
    session_id : str
    """
    return current_session().invalidate_user_session(session_id)
