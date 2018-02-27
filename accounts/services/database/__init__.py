"""Import db instance and define utility functions."""

import calendar
from datetime import datetime
import ipaddress
import json
from accounts.services.database.models import dbx
from accounts.services.database.models import TapirSession
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from flask_sqlalchemy import SQLAlchemy

from accounts.domain import UserData, SessionData, SessionCreationFailed
from accounts.context import get_application_config, get_application_global

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

    tapir_session: TapirSession = TapirSession(
        user_id = user_data.user_id,
        last_reissue = int(user_data.start_time),
        start_time = int(user_data.start_time) )

    data = json.dumps({
        'user_id': user_data.user_id,
        'user_name': user_data.user_name,
        'user_email': user_data.user_email,

        'start_time': user_data.start_time,
        'end_time': user_data.end_time,
        'last_reissue': user_data.last_reissue,
        'ip_address': user_data.ip_address,
        'remote_host': user_data.remote_host,
        'tracking_cookie': user_data.tracking_cookie,

        'scopes': user_data.scopes
    })

    try:
        db.session.add(tapir_session)
    except Exception as e:
        raise SessionCreationFailed(f'Failed to create: {e}') from e

    return SessionData(tapir_session.session_id, data)