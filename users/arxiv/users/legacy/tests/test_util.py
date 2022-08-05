"""Tests for :mod:`legacy_users.util`."""

from unittest import TestCase
from ..exceptions import PasswordAuthenticationFailed
from .util import temporary_db
from .. import util, models, sessions

from hypothesis import given, settings
from hypothesis import strategies as st
import string

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

class TestCheckPassword(TestCase):
    """
    Tests passwords.
    """
    @given(st.text(alphabet=string.printable))
    @settings(max_examples=500)
    def test_check_passwords_successful(self, passw):
        encrypted = util.hash_password(passw)
        self.assertTrue( util.check_password(passw, encrypted.encode('ascii')),
                         f"should work for password '{passw}'")

    @given(st.text(alphabet=string.printable), st.text(alphabet=st.characters()))
    @settings(max_examples=5000)
    def test_check_passwords_fuzz(self, passw, fuzzpw):
        if passw == fuzzpw:
            self.assertTrue(util.check_password(fuzzpw,
                                util.hash_password(passw).encode('ascii')))
        else:
            with self.assertRaises(PasswordAuthenticationFailed):
                util.check_password(fuzzpw,
                                    util.hash_password(passw).encode('ascii'))
