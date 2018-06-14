"""Import db instance and define utility functions."""

import ipaddress
import json
from datetime import datetime
from contextlib import contextmanager
import hashlib
from base64 import b64encode, b64decode

from typing import Optional, Generator, Tuple

from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from arxiv.base.globals import get_application_config, get_application_global
from arxiv.base import logging

from accounts.domain import User, UserSession
from accounts.services.exceptions import SessionCreationFailed, \
    SessionDeletionFailed, UserSessionUnknown

from .models import Base, TapirSession, TapirSessionsAudit

logger = logging.getLogger(__name__)


def _now() -> int:
    epoch = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
    return int(round(epoch))


@contextmanager
def transaction() -> Generator:
    """Context manager for database transaction."""
    session = _current_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        # logger.debug('Commit failed, rolling back: %s', str(e))
        session.rollback()
        raise


def _get_user_session(session_id: str) -> TapirSession:
    """Get TapirSession from session id."""
    with transaction() as session:
        db_session: TapirSession = session.query(TapirSession) \
            .filter(TapirSession.session_id == session_id) \
            .first()
    if not db_session:
        logger.error(f'No session found with id {session_id}')
        raise UserSessionUnknown('No such session')
    return db_session


def create_user_session(user: User, ip_address: str, remote_host: str,
                        tracking_cookie: str = '') -> UserSession:
    """
    Create a new legacy session for an authenticated user.

    Parameters
    ----------
    user : :class:`.User`
    ip_address : str
        Client IP address.
    remote_host : str
        Client hostname.
    tracking_cookie : str
        Tracking cookie payload from client request.

    Returns
    -------
    :class:`.Session`

    """
    config = get_application_config()
    start = _now()
    try:
        with transaction() as session:
            tapir_session = TapirSession(
                user_id=user.user_id,
                last_reissue=0,   # TODO: do we need this?
                start_time=start,
                end_time=0
            )

            tapir_sessions_audit = TapirSessionsAudit(
                session_id=tapir_session.session_id,
                ip_addr=ip_address,
                remote_host=remote_host,
                tracking_cookie=tracking_cookie
            )
            session.add(tapir_session)
            session.add(tapir_sessions_audit)
            session.commit()
    except Exception as e:  # TODO: be more specific.
        raise SessionCreationFailed(f'Failed to create: {e}') from e

    session_key = _pack_cookie(
        str(tapir_session.session_id),
        user.user_id,
        ip_address,
        str(user.privileges.classic),
        config['CLASSIC_SESSION_HASH']
    )
    return UserSession(
        str(tapir_session.session_id),
        session_key,
        user=user,
        start_time=start
    )

def invalidate_user_session(session_cookie: str) -> None:
    """
    Invalidate a legacy user session.

    Parameters
    ----------
    session_cookie : str
        Session cookie generated when the session was created.

    Raises
    ------
    :class:`UserSessionUnknown`
        The session could not be found, or the cookie was not valid.

    """
    config = get_application_config()
    session_id, user_id, ip, capabilities = _unpack_cookie(
        session_cookie,
        config['CLASSIC_SESSION_HASH']
    )
    end = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
    try:
        with transaction() as session:
            tapir_session = _get_user_session(session_id)
            tapir_session.end_time = end
            session.merge(tapir_session)
    except NoResultFound as e:
        raise UserSessionUnknown(f'No such session {session_id}') from e
    except SQLAlchemyError as e:
        raise IOError(f'Database error') from e


def _unpack_cookie(session_cookie: str, session_hash: str) \
        -> Tuple[str, str, str, int, str]:
    parts = session_cookie.split(':')
    payload = tuple(part for part in parts[:-1])
    try:
        expected_cookie = _pack_cookie(*payload, session_hash)
        assert expected_cookie == session_cookie
    except (TypeError, AssertionError) as e:
        raise UserSessionUnknown('Invalid session cookie; forged?') from e
    return payload


def _pack_cookie(session_id: str, user_id: str, ip: str, capabilities: int,
                 session_hash: str) -> bytes:
    """
    Generate a value for the classic session cookie.

    Parameters
    ----------
    session_id : str
    user_id : str
    ip : str
        Client IP address.
    capabilities : str
        This is essentially a user privilege level.
    session_hash : str
        System secret for signing sessions.

    Returns
    -------
    bytes
        Signed cookie value.

    """
    value = ':'.join(map(str, [session_id, user_id, ip, capabilities]))
    to_sign = f'{value}-{session_hash}'.encode('utf-8')
    cookie_hash = b64encode(hashlib.sha256(to_sign).digest())
    return value + ':' + cookie_hash.decode('utf-8')


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('CLASSIC_DATABASE_URI', 'sqlite://')


def _get_engine(app: object = None) -> Engine:
    """Get a new :class:`.Engine` for the classic database."""
    config = get_application_config(app)
    database_uri = config.get('CLASSIC_DATABASE_URI', 'sqlite://')
    return create_engine(database_uri)


def _get_session(app: object = None) -> Session:
    """Get a new :class:`.Session` for the classic database."""
    engine = _current_engine()
    return sessionmaker(bind=engine)()


def _current_engine() -> Engine:
    """Get/create :class:`.Engine` for this context."""
    g = get_application_global()
    if not g:
        return _get_engine()
    if 'classic_engine' not in g:
        g.classic_engine = _get_engine()
    return g.classic_engine


def _current_session() -> Session:
    """Get/create database session for this context."""
    g = get_application_global()
    if not g:
        return _get_session()
    if 'classic_session_store' not in g:
        g.classic_session_store = _get_session()
    return g.classic_session_store


def create_all() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(_current_engine())


def drop_all() -> None:
    """Drop all tables in the database."""
    Base.metadata.drop_all(_current_engine())
