"""Import db instance and define utility functions."""

import ipaddress
from accounts.services.database.models import dbx
from accounts.services.database.models import TapirSession, \
    MemberInstitutionIP
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
        stmt = (
            db.session.query(
                TapirSession.session_id
            )
        )

        session: TapirSession = db.session.query(stmt.c.label) .one()

        return session
    except NoResultFound:
        return None
    except SQLAlchemyError as e:
        raise IOError('Database error: %s' % e) from e
