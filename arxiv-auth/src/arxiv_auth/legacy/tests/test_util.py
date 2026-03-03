"""Tests for :mod:`legacy_users.util`."""

from unittest import TestCase
from .util import temporary_db
from .. import util, models, sessions

class TestGetSession(TestCase):
    """
    Tests for private function :func:`._load`.

    Gets a :class:`.DBSession` given a session ID.
    """

    def test_load_returns_a_session(self) -> None:
        """If ID matches a known session, returns a :class:`.DBSession`."""
        session_id = "424242424"
        with temporary_db() as db_session:
            start = util.now()
            db_session.add(models.DBSession(
                session_id=session_id,
                user_id=12345,
                last_reissue=start,
                start_time=start,
                end_time=0
            ))

            tapir_session = sessions._load(session_id)
            self.assertIsNotNone(tapir_session, 'verifying we have a session')
            self.assertEqual(tapir_session.session_id, int(session_id),
                             "Returned session has correct session id.")

