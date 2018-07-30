"""
Internal service API for the distributed session store.

Used to create, delete, and verify user and client session.
"""

import json
import time
import uuid
import random
from datetime import datetime, timedelta
import dateutil.parser
from pytz import timezone

from typing import Any, Optional, Union, Tuple

from functools import wraps
import redis
import jwt

from ... import domain
from ..exceptions import SessionCreationFailed, InvalidToken, \
    SessionDeletionFailed, UnknownSession, ExpiredToken

from arxiv.base.globals import get_application_config, get_application_global
from arxiv.base import logging

logger = logging.getLogger(__name__)
EASTERN = timezone('US/Eastern')


def _generate_nonce(length: int = 8) -> str:
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class SessionStore(object):
    """
    Manages a connection to Redis.

    In reality, the StrictRedis instance is thread safe, and connections are
    attached at the time a command is executed. This class simply provides a
    container for configuration.
    """

    def __init__(self, host: str, port: int, db: int, secret: str,
                 duration: int = 7200, token: str = None) -> None:
        """Open the connection to Redis."""
        params = dict(host=host, port=port, db=db)
        if token is not None:
            params.update({'password': token})
        self.r = redis.StrictRedis(**params)
        self._secret = secret
        self._duration = duration

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
        start_time = datetime.now(tz=EASTERN)
        end_time = start_time + timedelta(seconds=self._duration)
        session = domain.Session(
            session_id=session_id,
            user=user,
            start_time=start_time,
            end_time=end_time,
            authorizations=authorizations,
            nonce=_generate_nonce()
        )
        cookie = self._pack_cookie({
            'user_id': user.user_id,
            'session_id': session_id,
            'nonce': session.nonce,
            'expires': end_time.isoformat()
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
        cookie : str

        """
        try:
            session = domain.to_dict(self.load(cookie))
        except redis.exceptions.ConnectionError as e:
            raise SessionDeletionFailed(f'Connection failed: {e}') from e
        except InvalidToken as e:
            logger.debug('Could not load session data: %s', e)
            raise SessionDeletionFailed(f'Failed to delete: {e}') from e
        except ExpiredToken as e:
            # This is what we set out to do; our work here is done.
            logger.debug('Session already expired')
            return None
        try:
            cookie_data = self._unpack_cookie(cookie)
        except jwt.exceptions.DecodeError as e:   # type: ignore
            raise SessionDeletionFailed('Bad session token') from e

        try:
            if session['nonce'] != cookie_data['nonce'] \
                    or session['user']['user_id'] != cookie_data['user_id']:
                raise SessionDeletionFailed('Bad session token')
            session['end_time'] = datetime.now(tz=EASTERN).isoformat()
            self.r.set(session['session_id'], json.dumps(session))
        except redis.exceptions.ConnectionError as e:
            raise SessionDeletionFailed(f'Connection failed: {e}') from e
        except Exception as e:
            raise SessionDeletionFailed(f'Failed to delete: {e}') from e

    def invalidate_by_id(self, session_id: str) -> None:
        """
        Invalidate a session in the key-value store by ID.

        Parameters
        ----------
        session_id : str
        """
        try:
            session_data = domain.to_dict(self._load(session_id))
        except redis.exceptions.ConnectionError as e:
            raise SessionDeletionFailed(f'Connection failed: {e}') from e
        except InvalidToken as e:
            logger.debug('Could not load session data: %s', e)
            raise SessionDeletionFailed(f'Failed to delete: {e}') from e
        except ExpiredToken as e:
            # This is what we set out to do; our work here is done.
            logger.debug('Session already expired')
            return None

        session_data['end_time'] = datetime.now(tz=EASTERN).isoformat()
        try:
            self.r.set(session_id, json.dumps(session_data))
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
            expires = dateutil.parser.parse(cookie_data['expires'])
            nonce = cookie_data['nonce']
        except (KeyError, jwt.exceptions.DecodeError) as e:    # type: ignore
            raise InvalidToken('Token payload malformed') from e

        if expires <= datetime.now(tz=EASTERN):
            raise InvalidToken('Session has expired')

        session = self._load(session_id)
        if session.expired:
            raise ExpiredToken('Session has expired')
        if nonce != session.nonce:
            raise InvalidToken('Invalid token; likely a forgery')
        if session.user is None and session.client is None:
            raise InvalidToken('Neither user nor client data are present')
        if user_id and session.user is not None \
                and user_id != session.user.user_id:
            raise InvalidToken('Invalid token; likely a forgery')
        if client_id and session.client is not None \
                and client_id != session.client.client_id:
            raise InvalidToken('Invalid token; likely a forgery')
        return session

    def _load(self, session_id: str) -> domain.Session:
        """Get session data by session ID."""
        user_session: Union[str, bytes, bytearray] = self.r.get(session_id)
        if not user_session:
            logger.error(f'No such session: {session_id}')
            raise UnknownSession(f'Failed to find session {session_id}')
        try:
            data: dict = json.loads(user_session)
        except json.decoder.JSONDecodeError:
            raise InvalidToken('Invalid or corrupted session token')
        session: domain.Session = domain.from_dict(domain.Session, data)
        return session

    def _unpack_cookie(self, cookie: str) -> dict:
        secret = self._secret
        return dict(jwt.decode(cookie, secret))

    def _pack_cookie(self, cookie_data: dict) -> str:
        secret = self._secret
        return jwt.encode(cookie_data, secret).decode('ascii')


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('REDIS_HOST', 'localhost')
    config.setdefault('REDIS_PORT', '6379')
    config.setdefault('REDIS_DATABASE', '0')
    config.setdefault('REDIS_TOKEN', None)
    config.setdefault('JWT_SECRET', 'foosecret')
    config.setdefault('SESSION_DURATION', '7200')


def get_redis_session(app: object = None) -> SessionStore:
    """Get a new session with the search index."""
    config = get_application_config(app)
    host = config.get('REDIS_HOST', 'localhost')
    port = int(config.get('REDIS_PORT', '6379'))
    db = int(config.get('REDIS_DATABASE', '0'))
    token = config.get('REDIS_TOKEN', None)
    secret = config['JWT_SECRET']
    duration = int(config.get('SESSION_DURATION', '7200'))
    return SessionStore(host, port, db, secret, duration, token=token)


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
    return current_session().create(user, authorizations, ip_address,
                                    remote_host, tracking_cookie)


@wraps(SessionStore.load)
def load(cookie: str) -> domain.Session:
    """
    Load a session by cookie value.

    Parameters
    ----------
    cookie : str

    Returns
    -------
    dict
    """
    return current_session().load(cookie)


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
def invalidate(cookie: str) -> None:
    """
    Invalidate a session in the key-value store.

    Parameters
    ----------
    cookie : str

    """
    return current_session().invalidate(cookie)


@wraps(SessionStore.invalidate_by_id)
def invalidate_by_id(session_id: str) -> None:
    """
    Invalidate a session in the key-value store by identifier.

    Parameters
    ----------
    session_id : str

    """
    return current_session().invalidate_by_id(session_id)
