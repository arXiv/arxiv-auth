"""Provides API for legacy user sessions."""

import ipaddress
import json
from datetime import datetime
import hashlib
from base64 import b64encode, b64decode

from typing import Optional, Generator, Tuple, List

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from .. import domain
from arxiv.base import logging

from .models import Base, DBSession, DBSessionsAudit, DBUser, DBEndorsement, \
    DBUserNickname
from .exceptions import SessionUnknown, SessionCreationFailed, \
    SessionDeletionFailed, SessionExpired
from .util import transaction, now, pack_cookie, unpack_cookie, \
    compute_capabilities, get_scopes, get_endorsements, from_epoch, epoch

logger = logging.getLogger(__name__)

_JoinedRow = Tuple[DBUser, DBSession, DBUserNickname, DBEndorsement]


def _load(session_id: str) -> DBSession:
    """Get DBSession from session id."""
    with transaction() as session:
        db_session: DBSession = session.query(DBSession) \
            .filter(DBSession.session_id == session_id) \
            .first()
    if not db_session:
        logger.error(f'No session found with id {session_id}')
        raise SessionUnknown('No such session')
    return db_session


def load(session_cookie: str) -> domain.Session:
    """
    Given a session cookie (from request), load the logged-in user.

    Parameters
    ----------
    session_cookie : str
        Legacy cookie value passed with the request.

    Returns
    -------
    :class:`.domain.Session`

    Raises
    ------
    :class:`.SessionExpired`
    :class:`.SessionUnknown`

    """
    session_id, user_id, ip_addr, capabilities = unpack_cookie(session_cookie)

    with transaction() as session:
        data: List[_JoinedRow] = (
            session.query(DBUser, DBSession, DBUserNickname)
            .filter(DBUser.user_id == user_id)
            .filter(DBUserNickname.user_id == user_id)
            .filter(DBSession.user_id == user_id)
            .filter(DBSession.session_id == session_id)
            .first()
        )

        if not data:
            raise SessionUnknown('No such user or session')

        db_user, db_session, db_nick = data

        # Verify that the session is not expired.
        if db_session.end_time != 0 and db_session.end_time < now():
            logger.info('Session has expired: %s', session_id)
            raise SessionExpired(f'Session {session_id} has expired')

        user = domain.User(
            user_id=str(user_id),
            username=db_nick.nickname,
            email=db_user.email,
            name=domain.UserFullName(
                forename=db_user.first_name,
                surname=db_user.last_name,
                suffix=db_user.suffix_name
            )
        )

        # We should get one row per endorsement.
        authorizations = domain.Authorizations(
            classic=compute_capabilities(db_user),
            endorsements=get_endorsements(db_user),
            scopes=get_scopes(db_user)
        )

    return domain.Session(
        str(db_session.session_id),
        start_time=from_epoch(db_session.start_time),
        user=user,
        authorizations=authorizations
    )


def create(user: domain.User, authorizations: domain.Authorizations,
           ip_address: str, remote_host: str, tracking_cookie: str = '') \
        -> Tuple[domain.Session, str]:
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
    start = datetime.now()
    try:
        with transaction() as session:
            tapir_session = DBSession(
                user_id=user.user_id,
                last_reissue=0,   # TODO: do we need this?
                start_time=epoch(start),
                end_time=0
            )
            tapir_sessions_audit = DBSessionsAudit(
                session=tapir_session,
                ip_addr=ip_address,
                remote_host=remote_host,
                tracking_cookie=tracking_cookie
            )
            session.add(tapir_sessions_audit)
            session.commit()
    except Exception as e:  # TODO: be more specific.
        raise SessionCreationFailed(f'Failed to create: {e}') from e

    cookie = pack_cookie(
        str(tapir_session.session_id),
        user.user_id,
        ip_address,
        str(authorizations.classic)
    )
    session = domain.Session(
        str(tapir_session.session_id),
        user=user,
        start_time=start,
        authorizations=authorizations
    )
    return session, cookie


def invalidate(cookie: str) -> None:
    """
    Invalidate a legacy user session.

    Parameters
    ----------
    cookie : str
        Session cookie generated when the session was created.

    Raises
    ------
    :class:`SessionUnknown`
        The session could not be found, or the cookie was not valid.

    """
    session_id, user_id, ip, capabilities = unpack_cookie(cookie)
    end = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
    try:
        with transaction() as session:
            tapir_session = _load(session_id)
            tapir_session.end_time = end - 1
            session.merge(tapir_session)
    except NoResultFound as e:
        raise SessionUnknown(f'No such session {session_id}') from e
    except SQLAlchemyError as e:
        raise IOError(f'Database error') from e
