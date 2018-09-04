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
import rediscluster

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

    In fact, the StrictRedis instance is thread safe and connections are
    attached at the time a command is executed. This class simply provides a
    container for configuration.
    """

    def __init__(self, host: str, port: int, db: int, secret: str,
                 duration: int = 7200, token: str = None) -> None:
        """Open the connection to Redis."""
        # params = #, db=db)
        logger.debug('New Redis connection at %s, port %s', host, port)
        self.r = rediscluster.StrictRedisCluster(
            startup_nodes=[{'host': host, 'port': str(port)}],
            skip_full_coverage_check=True
        )
        self._secret = secret
        self._duration = duration

    def create(self, authorizations: domain.Authorizations,
               ip_address: str, remote_host: str, tracking_cookie: str = '',
               user: Optional[domain.User] = None,
               client: Optional[domain.Client] = None,
               session_id: Optional[str] = None) -> domain.Session:
        """
        Create a new session.

        Parameters
        ----------
        authorizations : :class:`domain.Authorizations`
        ip_address : str
        remote_host : str
        tracking_cookie : str
        user : :class:`domain.User`
        client : :class:`domain.Client`

        Returns
        -------
        :class:`.Session`
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        start_time = datetime.now(tz=EASTERN)
        end_time = start_time + timedelta(seconds=self._duration)
        session = domain.Session(
            session_id=session_id,
            user=user,
            client=client,
            start_time=start_time,
            end_time=end_time,
            authorizations=authorizations,
            nonce=_generate_nonce()
        )

        try:
            self.r.set(session_id, json.dumps(domain.to_dict(session)),
                       ex=self._duration)
        except redis.exceptions.ConnectionError as e:
            raise SessionCreationFailed(f'Connection failed: {e}') from e
        except Exception as e:
            raise SessionCreationFailed(f'Failed to create: {e}') from e

        return session

    def generate_cookie(self, session: domain.Session) -> str:
        """Generate a cookie from a :class:`domain.Session`."""
        return self._pack_cookie({
            'user_id': session.user.user_id,
            'session_id': session.session_id,
            'nonce': session.nonce,
            'expires': session.end_time.isoformat()
        })

    def delete(self, cookie: str) -> None:
        """
        Delete a session.

        Parameters
        ----------
        cookie : str
        """
        cookie_data = self._unpack_cookie(cookie)
        self.delete_by_id(cookie_data['session_id'])

    def delete_by_id(self, session_id: str) -> None:
        """
        Delete a session in the key-value store by ID.

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
        try:    # Load the current session data from the session store.
            session = self.load(cookie)
            session_data = domain.to_dict(session)
            self.validate_session_against_cookie(session, cookie)
        except ExpiredToken as e:
            # This is what we set out to do; our work here is done.
            logger.debug('Session already expired')
            return None
        except Exception as e:
            # Something went terribly wrong.
            logger.debug('Could not load session data: %s', e)
            raise SessionDeletionFailed(f'Failed to delete: {e}') from e

        try:
            session_data['end_time'] = datetime.now(tz=EASTERN).isoformat()
            self.r.set(session_data['session_id'], json.dumps(session_data))
        except Exception as e:
            raise SessionDeletionFailed(f'Failed to delete: {e}') from e

    def validate_session_against_cookie(self, session: domain.Session,
                                        cookie: str) -> None:
        """
        Validate session data against a cookie.

        Parameters
        ----------
        session : :class:`Session`
        cookie : str

        Raises
        ------
        :class:`InvalidToken`
            Raised if the data in the cookie does not match the session data.
        """
        cookie_data = self._unpack_cookie(cookie)
        if cookie_data['nonce'] != session.nonce \
                or session.user.user_id != cookie_data['user_id']:
            raise InvalidToken('Invalid token; likely a forgery')

    def invalidate_by_id(self, session_id: str) -> None:
        """
        Invalidate a session in the key-value store by session ID.

        Parameters
        ----------
        session_id : str
        """
        try:
            session_data = domain.to_dict(self.load_by_id(session_id))
        except ExpiredToken as e:
            # This is what we set out to do; our work here is done.
            logger.debug('Session already expired')
            return None
        except Exception as e:
            logger.debug('Could not load session data: %s', e)
            raise SessionDeletionFailed(f'Connection failed: {e}') from e

        session_data['end_time'] = datetime.now(tz=EASTERN).isoformat()
        try:
            self.r.set(session_id, json.dumps(session_data))
        except Exception as e:
            raise SessionDeletionFailed(f'Failed to delete: {e}') from e

    def load(self, cookie: str) -> domain.Session:
        """Load a session using a session cookie."""
        try:
            cookie_data = self._unpack_cookie(cookie)
            expires = dateutil.parser.parse(cookie_data['expires'])
        except (KeyError, jwt.exceptions.DecodeError) as e:    # type: ignore
            raise InvalidToken('Token payload malformed') from e

        if expires <= datetime.now(tz=EASTERN):
            raise InvalidToken('Session has expired')

        session = self.load_by_id(cookie_data['session_id'])
        if session.expired:
            raise ExpiredToken('Session has expired')
        if session.user is None and session.client is None:
            raise InvalidToken('Neither user nor client data are present')

        self.validate_session_against_cookie(session, cookie)
        return session

    def load_by_id(self, session_id: str) -> domain.Session:
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
        try:
            data = dict(jwt.decode(cookie, secret))
        except jwt.exceptions.DecodeError as e:   # type: ignore
            raise InvalidToken('Session cookie is malformed') from e
        return data

    def _pack_cookie(self, cookie_data: dict) -> str:
        secret = self._secret
        return jwt.encode(cookie_data, secret).decode('ascii')


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('REDIS_HOST', 'localhost')
    config.setdefault('REDIS_PORT', '7000')
    config.setdefault('REDIS_DATABASE', '0')
    config.setdefault('REDIS_TOKEN', None)
    config.setdefault('JWT_SECRET', 'foosecret')
    config.setdefault('SESSION_DURATION', '7200')


def get_redis_session(app: object = None) -> SessionStore:
    """Get a new session with the search index."""
    config = get_application_config(app)
    host = config.get('REDIS_HOST', 'localhost')
    port = int(config.get('REDIS_PORT', '7000'))
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
def create(authorizations: domain.Authorizations,
           ip_address: str, remote_host: str, tracking_cookie: str = '',
           user: Optional[domain.User] = None,
           client: Optional[domain.Client] = None,
           session_id: Optional[str] = None) -> domain.Session:
    """Create a new session."""
    return current_session().create(authorizations, ip_address,
                                    remote_host, tracking_cookie,
                                    user=user, client=client,
                                    session_id=session_id)


@wraps(SessionStore.load)
def load(cookie: str) -> domain.Session:
    """Load a session by cookie value."""
    return current_session().load(cookie)


@wraps(SessionStore.load)
def load_by_id(session_id: str) -> domain.Session:
    """Load a session by session ID."""
    return current_session().load_by_id(session_id)


@wraps(SessionStore.delete)
def delete(cookie: str) -> None:
    """Delete a session in the key-value store."""
    return current_session().delete(cookie)


@wraps(SessionStore.delete_by_id)
def delete_by_id(session_id: str) -> None:
    """Delete a session in the key-value store by ID."""
    return current_session().delete_by_id(session_id)


@wraps(SessionStore.invalidate)
def invalidate(cookie: str) -> None:
    """Invalidate a session in the key-value store."""
    return current_session().invalidate(cookie)


@wraps(SessionStore.invalidate_by_id)
def invalidate_by_id(session_id: str) -> None:
    """Invalidate a session in the key-value store by identifier."""
    return current_session().invalidate_by_id(session_id)


@wraps(SessionStore.generate_cookie)
def generate_cookie(session: domain.Session) -> str:
    """Generate a cookie from a :class:`domain.Session`."""
    return current_session().generate_cookie(session)
