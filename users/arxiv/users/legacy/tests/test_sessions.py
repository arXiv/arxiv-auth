"""Tests for legacy_users service."""
import time
from typing import Optional
from unittest import mock, TestCase
from datetime import datetime

from .. import exceptions, sessions, util, models

from .util import temporary_db


class TestCreateSession(TestCase):
    """Tests for public function :func:`.`."""

    def test_create(self):
        """Accept a :class:`.User` and returns a :class:`.Session`."""
        user = sessions.domain.User(
            user_id="1",
            username='theuser',
            email='the@user.com',
        )
        auths = sessions.domain.Authorizations(classic=6)
        ip_address = '127.0.0.1'
        remote_host = 'foo-host.foo.com'
        tracking = "1.foo"
        with temporary_db():
            user_session, cookie = sessions.create(user, auths, ip_address,
                                                   remote_host, tracking)

            self.assertIsInstance(user_session, sessions.domain.Session)
            tapir_session = sessions._load(user_session.session_id)
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
    """Tests for public function :func:`.invalidate`."""

    def test_invalidate(self):
        """The session is invalidated by settings `end_time`."""
        session_id = "424242424"
        user_id = "12345"
        ip = "127.0.0.1"
        capabilities = 6

        with temporary_db() as db_session:
            cookie = util.pack_cookie(session_id, user_id, ip, capabilities)
            start = (datetime.now() - datetime.utcfromtimestamp(0))\
                .total_seconds()
            with util.transaction() as db_session:
                tapir_session = models.DBSession(
                    session_id=session_id,
                    user_id=12345,
                    last_reissue=start,
                    start_time=start,
                    end_time=0
                )
                db_session.add(tapir_session)

            sessions.invalidate(cookie)
            tapir_session = sessions._load(session_id)
            time.sleep(1)
            self.assertGreaterEqual(util.now(), tapir_session.end_time)

    def test_invalidate_nonexistant_session(self):
        """An exception is raised if the session doesn't exist."""
        with temporary_db():
            with self.assertRaises(exceptions.SessionUnknown):
                sessions.invalidate('foosession')
