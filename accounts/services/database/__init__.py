"""Import db instance and define utility functions."""

import ipaddress
from accounts.services.database.models import dbx
from accounts.services.database.models import TapirSession
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from flask_sqlalchemy import SQLAlchemy

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
