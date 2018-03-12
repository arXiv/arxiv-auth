"""Tests for database service."""
import time

from unittest import mock, TestCase
from accounts.services import database
from accounts.services.database import TapirSession
from accounts.domain import SessionData, UserData

from typing import Optional

from flask import Flask


DATABASE_URL = 'sqlite:///:memory:'


class TestTapirSession(TestCase):
    """
    Test the following database methods:

    :func:`.get_session` gets a session given a session_id.
    """

    init_session_id: int = 424242424

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
        database.db.app = mock_app
        database.db.init_app(mock_app)
        database.db.create_all()
        issue_time =  int(time.time())
        inst_some_user1 = database.models.TapirSession(
            session_id = self.init_session_id,
            user_id= 12345,
            last_reissue = issue_time,
            start_time = issue_time,
            end_time = issue_time + 10000 # fix this arbitrary length
        )
        database.db.session.add(inst_some_user1)

    def test_get_session_returns_a_session(self) -> None:
        """If session_id matches a known session, a session is returned."""
        tapir_session: Optional[TapirSession] = database.get_session(self.init_session_id)
        self.assertIsNotNone(tapir_session, 'verifying we have a session')
        if tapir_session is not None:
            self.assertEqual(
                tapir_session.session_id,
                self.init_session_id,
                "Returned session has correct session id."
            )

    def test_create_session(self):
        """Accepts a :class:`.UserData` and returns a :class:`.SessionData`."""

        user_data = UserData(
            user_id=1,
            start_time=time.time(),
            end_time=time.time() + 30*60*1000,
            last_reissue=0,
            ip_address='127.0.0.1',
            remote_host='foo-host.foo.com',
            user_name='theuser',
            user_email='the@user.com',
            scopes=['foo:write']
        )
        session = database.create_session(user_data)
        self.assertIsInstance(session, SessionData)
        self.assertIsNotNone(session, 'verifying we have a session')
        self.assertTrue(session.session_id == self.init_session_id + 1)

        tapir_session: Optional[TapirSession] = database.get_session(session.session_id)
        self.assertIsNotNone(session, 'verifying we have a session')
        if tapir_session is not None:
            self.assertEqual(
                tapir_session.session_id,
                session.session_id,
                "Returned session has correct session id."
            )
            self.assertEqual(
                tapir_session.user_id,
                user_data.user_id,
                "Returned session has correct user id."
            )
            self.assertEqual(
                tapir_session.last_reissue,
                int(user_data.last_reissue),
                "Returned session has correct last_reissue time."
            )
            self.assertEqual(
                tapir_session.start_time,
                int(user_data.start_time),
                "Returned session has correct start time."
            )
            self.assertEqual(
                tapir_session.end_time,
                int(user_data.end_time),
                "Returned session has correct end time."
            )

        self.assertTrue(bool(session.data))

    def test_invalidate_session(self):
        """Invalidates a session from the datastore."""

        user_data = UserData(
            user_id=1,
            start_time=time.time() - 30*60,
            end_time=time.time() + 30*60,
            last_reissue=0,
            ip_address='127.0.0.1',
            remote_host='foo-host.foo.com',
            user_name='theuser',
            user_email='the@user.com',
            scopes=['foo:write']
        )

        session0: SessionData = database.create_session(user_data)
        self.assertIsInstance(session0, SessionData)
        self.assertIsNotNone(session0, 'verifying we have a session')
        self.assertGreaterEqual(user_data.end_time, time.time())

        database.invalidate_session(session0.session_id)

        tapir_session: Optional[TapirSession] = database.get_session(session0.session_id)
        self.assertIsNotNone(tapir_session, 'verifying we have a session')
        if tapir_session is not None:
            self.assertGreaterEqual(time.time(), tapir_session.end_time)
        
    def tearDown(self) -> None:
        """Close the database session and drop all tables."""
        database.db.session.remove()
        database.db.drop_all()
