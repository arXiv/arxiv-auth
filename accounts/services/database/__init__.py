"""Import db instance and define utility functions."""

import ipaddress
import json
import time
import uuid
from accounts.services.database.models import dbx
from accounts.services.database.models import TapirSession, TapirSessionsAudit
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from flask_sqlalchemy import SQLAlchemy

from accounts.domain import UserData, SessionData
from accounts.context import get_application_config, get_application_global
from accounts.services.exceptions import *

from typing import Optional

# Temporary fix for https://github.com/python/mypy/issues/4049 :
db: SQLAlchemy = dbx

def get_session(id: int) -> Optional[TapirSession]:
    """Get TapirSession from session id."""
    try:

        # session.query(User).filter(User.name.in_(['ed', 'fakeuser'])).all()
        session: TapirSession = db.session.query(TapirSession) \
            .filter(TapirSession.session_id.in_([id])) \
            .one()

        return session
    except NoResultFound:
        return None
    except SQLAlchemyError as e:
        raise IOError('Database error: %s' % e) from e

def create_session(user_data: UserData) -> SessionData:
    """
    Create a new legacy session.

    Parameters
    ----------
    user_data : :class:`.UserData`

    Returns
    -------
    :class:`.SessionData`
    """
    tapir_session = TapirSession(
        user_id=user_data.user_id,
        last_reissue=int(user_data.last_reissue),
        start_time=int(user_data.start_time),
        end_time=int(user_data.end_time)
    )

    tracking_cookie = user_data.ip_address + str(uuid.uuid4)

    tapir_sessions_audit = TapirSessionsAudit(
        session_id=tapir_session.session_id,
        ip_addr=user_data.ip_address,
        remote_host=user_data.remote_host,
        tracking_cookie=tracking_cookie
    )
    
    data = json.dumps({
        'tracking_cookie': tracking_cookie
    })

    try:
        db.session.add(tapir_session)
        db.session.add(tapir_sessions_audit)
        db.session.commit()
    except Exception as e:
        raise SessionCreationFailed(f'Failed to create: {e}') from e

    return SessionData(tapir_session.session_id, data)

def invalidate_session(session_id: int) -> None:
    """
    Invalidates a tapir session

    Parameters
    ----------
    session_id : int
    """
    try:
        tapir_session: Optional[TapirSession] = get_session(session_id)
        if tapir_session is not None:
            tapir_session.end_time = time.time()
            db.session.merge(tapir_session)
        else:
            raise SessionUnknown(f'Failed to find session {session_id}')
    except NoResultFound as ex:
        raise SessionUnknown(f'Failed to find session {session_id} for exception {ex}') from ex
    except SQLAlchemyError as ex:
        raise IOError('Database error: %s' % ex) from ex