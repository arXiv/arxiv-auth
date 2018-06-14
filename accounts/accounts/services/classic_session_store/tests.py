"""Tests for classic service."""
import time
from typing import Optional
from contextlib import contextmanager
from unittest import mock, TestCase
from datetime import datetime

from flask import Flask

from accounts.services import classic_session_store as store
from accounts.services.exceptions import UserSessionUnknown, \
    SessionCreationFailed, SessionDeletionFailed
from accounts.domain import UserSession, User, UserPrivileges


DATABASE_URL = 'sqlite:///:memory:'


@contextmanager
def in_memory_db():
    """Provide an in-memory sqlite database for testing purposes."""
    app = Flask('foo')
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CLASSIC_SESSION_HASH'] = 'foohash'

    with app.app_context():
        store.init_app(app)
        store.create_all()
        try:
            yield store._current_session()
        except Exception:
            raise
        finally:
            store.drop_all()


class TestGetSession(TestCase):
    """
    Tests for private function :func:`._get_user_session`.

    Gets a :class:`.TapirSession` given a session ID.
    """

    def test_get_user_session_returns_a_session(self) -> None:
        """If ID matches a known session, returns a :class:`.TapirSession`."""
        session_id = "424242424"
        with in_memory_db() as db_session:
            start = (datetime.now() - datetime.utcfromtimestamp(0)) \
                .total_seconds()
            db_session.add(store.models.TapirSession(
                session_id=session_id,
                user_id=12345,
                last_reissue=start,
                start_time=start,
                end_time=0
            ))

            tapir_session = store._get_user_session(session_id)
            self.assertIsNotNone(tapir_session, 'verifying we have a session')
            self.assertEqual(tapir_session.session_id, int(session_id),
                             "Returned session has correct session id.")


class TestCreateSession(TestCase):
    """Tests for public function :func:`.`."""

    def test_create_user_session(self):
        """Accept a :class:`.User` and returns a :class:`.Session`."""
        user = User(
            user_id="1",
            username='theuser',
            email='the@user.com',
            privileges=UserPrivileges(classic=2)
        )
        ip_address = '127.0.0.1'
        remote_host = 'foo-host.foo.com'
        tracking = "1.foo"
        with in_memory_db():
            user_session = store.create_user_session(user, ip_address,
                                                     remote_host, tracking)

            self.assertIsInstance(user_session, UserSession)

            tapir_session = store._get_user_session(user_session.session_id)
            self.assertIsNotNone(user_session, 'verifying we have a session')
            if tapir_session is not None:
                self.assertEqual(
                    tapir_session.session_id,
                    int(user_session.session_id),
                    "Returned session has correct session id."
                )
                self.assertEqual(tapir_session.user_id, int(user.user_id),
                                 "Returned session has correct user id.")
                self.assertEqual(tapir_session.end_time, 0,
                                 "End time is 0 (no end time)")


class TestInvalidateSession(TestCase):
    """Tests for public function :func:`.invalidate_user_session`."""

    def test_invalidate_user_session(self):
        """The session is invalidated by settings `end_time`."""
        session_id = "424242424"
        user_id = "12345"
        ip = "127.0.0.1"
        capabilities = 6

        with in_memory_db() as db_session:
            cookie = store._pack_cookie(session_id, user_id, ip, capabilities, 'foohash')
            start = (datetime.now() - datetime.utcfromtimestamp(0))\
                .total_seconds()
            with store.transaction() as db_session:
                tapir_session = store.models.TapirSession(
                    session_id=session_id,
                    user_id=12345,
                    last_reissue=start,
                    start_time=start,
                    end_time=0
                )
                db_session.add(tapir_session)

            store.invalidate_user_session(cookie)
            now = (datetime.now() - datetime.utcfromtimestamp(0)) \
                .total_seconds()
            tapir_session = store._get_user_session(session_id)
            self.assertGreaterEqual(now, tapir_session.end_time)

    def test_invalidate_nonexistant_session(self):
        """An exception is raised if the session doesn't exist."""
        with in_memory_db():
            with self.assertRaises(UserSessionUnknown):
                store.invalidate_user_session('foosession')
