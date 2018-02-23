"""Tests for database service."""
import time

from unittest import mock, TestCase
from accounts.services import database
from accounts.services.database import TapirSession

from typing import Optional


DATABASE_URL = 'sqlite:///:memory:'


class TestTapirSession(TestCase):
    """
    Test the following database methods:

    :func:`.get_session` gets a session given a session_id.
    """

    def setUp(self) -> None:
        """
        Initialize a database session with in-memory SQLite and creates a
        session entry.
        """

        mock_app = mock.MagicMock()
        mock_app.config = {'SQLALCHEMY_DATABASE_URI': DATABASE_URL,
                           'SQLALCHEMY_TRACK_MODIFICATIONS': False
        }

        mock_app.extensions = {}
        mock_app.root_path = ''

        database.db.init_app(mock_app)
        database.db.app = mock_app
        database.db.create_all()
        issue_time =  int(time.time())
        inst_some_user1 = database.models.TapirSession(
            session_id = 424242424,
            user_id= 12345,
            last_reissue = issue_time,
            start_time = issue_time,
            end_time = issue_time + 10000 # fix this arbitrary length
        )
        database.db.session.add(inst_some_user1)

    def test_get_session_returns_a_session(self) -> None:
        """If session_id matches a known session, a session is returned."""
        session: Optional[TapirSession] = database.get_session(424242424)
        self.assertIsNotNone(session, 'verifying we have a session')
        if session is not None:
            self.assertEqual(session.session_id, 424242424, "Returned session has correct session id.")


    def tearDown(self) -> None:
        """Close the database session and drop all tables."""
        database.db.session.remove()
        database.db.drop_all()
