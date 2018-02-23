"""Provides a distributed session store."""

from functools import wraps
import uuid
import redis
import json

from accounts.domain import UserData, SessionData
from accounts.context import get_application_config, get_application_global


class SessionCreationFailed(RuntimeError):
    """Failed to create a session in the session store."""


class SessionDeletionFailed(RuntimeError):
    """Failed to delete a session in the session store."""


class RedisSession(object):
    """
    Manages a connection to Redis.

    In reality, the StrictRedis instance is thread safe, and connections are
    attached at the time a command is executed. This class simply provides a
    container for configuration.
    """

    def __init__(self, host: str, port: int, database: int) -> None:
        """Open the connection to Redis."""
        self.r = redis.StrictRedis(host=host, port=port, db=database)

    def create_session(self, user_data: UserData) -> SessionData:
        """
        Create a new session.

        Parameters
        ----------
        user_data : :class:`.UserData`

        Returns
        -------
        :class:`.SessionData`
        """
        session_id = str(uuid.uuid4())
        data = json.dumps({
            'user_id': user_data.user_id,
            'user_name': user_data.user_name,
            'user_email': user_data.user_email,

            'start_time': user_data.start_time,
            'end_time': user_data.end_time,
            'last_reissue': user_data.last_reissue,
            'ip_address': user_data.ip_address,
            'remote_host': user_data.remote_host,

            'scopes': user_data.scopes
        })

        try:
            self.r.set(session_id, data)
        except redis.exceptions.ConnectionError as e:
            raise SessionCreationFailed(f'Connection failed: {e}') from e
        except Exception as e:
            raise SessionCreationFailed(f'Failed to create: {e}') from e
        return SessionData(session_id, data)

    def delete_session(self, session_id: str) -> None:
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


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('REDIS_HOST', 'localhost')
    config.setdefault('REDIS_PORT', '6379')
    config.setdefault('REDIS_DATABASE', '0')


def get_session(app: object = None) -> RedisSession:
    """Get a new session with the search index."""
    config = get_application_config(app)
    host = config.get('REDIS_HOST', 'localhost')
    port = int(config.get('REDIS_PORT', '6379'))
    database = int(config.get('REDIS_DATABASE', '0'))
    return RedisSession(host, port, database)


def current_session() -> RedisSession:
    """Get/create :class:`.SearchSession` for this context."""
    g = get_application_global()
    if not g:
        return get_session()
    if 'redis' not in g:
        g.redis = get_session()     # type: ignore
    return g.redis      # type: ignore


@wraps(RedisSession.create_session)
def create_session(user_data: UserData) -> SessionData:
    """
    Create a new session.

    Parameters
    ----------
    user_data : :class:`.UserData`

    Returns
    -------
    :class:`.SessionData`
    """
    return current_session().create_session(user_data)


@wraps(RedisSession.delete_session)
def delete_session(session_id: str) -> None:
    """
    Delete a session in the key-value store.

    Parameters
    ----------
    session_id : str
    """
    return current_session().delete_session(session_id)
