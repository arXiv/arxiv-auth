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

    def create_session(self, user_data: UserData) -> SessionData:
        """
        Create a new legacy session.

        Parameters
        ----------
        user_data : :class:`.UserData`

        Returns
        -------
        :class:`.SessionData`
        """
        session_id = str(uuid.uuid4()) # need to see how integer is created in Auth.pm
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
            self.r.set(session_id, data)
        except redis.exceptions.ConnectionError as e:
            raise SessionCreationFailed(f'Connection failed: {e}') from e
        except Exception as e:
            raise SessionCreationFailed(f'Failed to create: {e}') from e

        return SessionData(session_id, data)