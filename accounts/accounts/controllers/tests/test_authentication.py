"""Tests for mod:`accounts.controllers`."""

from unittest import TestCase, mock
from datetime import datetime
from pytz import timezone, UTC

import hashlib
from base64 import b64encode
import os

from flask import Flask
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import BadRequest

from arxiv import status

from arxiv_auth import domain
from arxiv_auth.legacy import exceptions, util, models

from accounts.factory import create_web_app
from accounts.controllers.authentication import login, logout, LoginForm


EASTERN = timezone('US/Eastern')


def raise_authentication_failed(*args, **kwargs):
    """Simulate a failed login attempt at the backend service."""
    raise exceptions.AuthenticationFailed('nope')


class TestAuthenticationController(TestCase):
    """Tests for :func:`.logout`."""

    @classmethod
    def setUpClass(self):
        self.secret = 'bazsecret'
        self.db = 'db.sqlite'
        self.expiry = 500

    def setUp(self):
        self.ip_address = '10.1.2.3'
        self.environ_base = {'REMOTE_ADDR': self.ip_address}
        self.app = create_web_app()
        self.app.config['CLASSIC_COOKIE_NAME'] = 'foo_tapir_session'
        self.app.config['AUTH_SESSION_COOKIE_NAME'] = 'baz_session'
        self.app.config['AUTH_SESSION_COOKIE_SECURE'] = '0'
        self.app.config['SESSION_DURATION'] = self.expiry
        self.app.config['JWT_SECRET'] = self.secret
        self.app.config['CLASSIC_DATABASE_URI'] = f'sqlite:///{self.db}'
        self.app.config['CLASSIC_SESSION_HASH'] = 'xyz1234'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db}'
        self.app.config['REDIS_FAKE'] = True
        self.app.config['SERVER_NAME'] = 'example.com' # to do urls in emails

        with self.app.app_context():
            util.drop_all()
            util.create_all()

            with util.transaction() as session:
                # We have a good old-fashioned user.
                db_user = models.DBUser(
                    user_id=1,
                    first_name='first',
                    last_name='last',
                    suffix_name='iv',
                    email='first@last.iv',
                    policy_class=2,
                    flag_edit_users=1,
                    flag_email_verified=1,
                    flag_edit_system=0,
                    flag_approved=1,
                    flag_deleted=0,
                    flag_banned=0,
                    tracking_cookie='foocookie',
                )
                db_nick = models.DBUserNickname(
                    nick_id=1,
                    nickname='foouser',
                    user_id=1,
                    user_seq=1,
                    flag_valid=1,
                    role=0,
                    policy=0,
                    flag_primary=1
                )
                db_demo = models.DBProfile(
                    user_id=1,
                    country='US',
                    affiliation='Cornell U.',
                    url='http://example.com/bogus',
                    rank=2,
                    original_subject_classes='cs.OH',
                    )
                salt = b'fdoo'
                password = b'thepassword'
                hashed = hashlib.sha1(salt + b'-' + password).digest()
                encrypted = b64encode(salt + hashed)
                db_password = models.DBUserPassword(
                    user_id=1,
                    password_storage=2,
                    password_enc=encrypted
                )
                session.add(db_user)
                session.add(db_password)
                session.add(db_nick)
                session.add(db_demo)

    @mock.patch('accounts.controllers.authentication.SessionStore')
    @mock.patch('accounts.controllers.authentication.legacy_sessions')
    def test_logout(self, mock_legacy_ses, mock_SessionStore):
        """A logged-in user requests to log out."""
        mock_legacy_ses.invalidate_session.return_value = None
        mock_SessionStore.current_session.return_value \
            .delete.return_value = None
        next_page = '/'
        session_id = 'foosession'
        classic_id = 'bazsession'
        with self.app.app_context():
            data, status_code, header = logout(session_id, classic_id, next_page)
        self.assertEqual(status_code, status.HTTP_303_SEE_OTHER,
                         "Redirects user to next page")
        self.assertEqual(header['Location'], next_page,
                         "Redirects user to next page.")

    @mock.patch('accounts.controllers.authentication.SessionStore')
    @mock.patch('accounts.controllers.authentication.legacy_sessions')
    def test_logout_anonymous(self, mock_legacy_ses, mock_SessionStore):
        """An anonymous user requests to log out."""
        mock_legacy_ses.invalidate_session.return_value = None
        mock_SessionStore.current_session.return_value \
            .delete.return_value = None
        next_page = '/'
        with self.app.app_context():
            data, status_code, header = logout(None, None, next_page)
        self.assertEqual(status_code, status.HTTP_303_SEE_OTHER,
                         "Redirects user to next page")
        self.assertEqual(header['Location'], next_page,
                         "Redirects user to next page.")

    @mock.patch('accounts.controllers.authentication.SessionStore')
    def test_login(self, mock_SessionStore):
        """User requests the login page."""
        with self.app.app_context():
            data, status_code, header = login('GET', {}, '', '')
        self.assertIn('form', data)
        self.assertIsInstance(data['form'], LoginForm,
                              "Response includes a login form.")
        self.assertEqual(status_code, status.HTTP_200_OK)


    @mock.patch('accounts.controllers.authentication.SessionStore')
    def test_post_invalid_data(self, mock_SessionStore):
        """User submits invalid data."""
        form_data = MultiDict({'username': 'foouser'})     # Missing password.
        next_page = '/next'
        ip = '123.45.67.89'
        with self.app.app_context():
            data, status_code, header = login('POST', form_data, ip, next_page)
        self.assertIn('form', data)
        self.assertIsInstance(data['form'], LoginForm,
                              "Response includes a login form.")
        self.assertGreater(len(data['form'].password.errors), 0,
                           "Password field has an error")
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST,
                         "Response status is 400 bad request")

    @mock.patch('accounts.controllers.authentication.authenticate')
    def test_post_valid_data_bad_credentials(self, mock_authenticate):
        """Form data are valid but don't check out."""
        mock_authenticate.side_effect = raise_authentication_failed

        form_data = MultiDict({'username': 'foouser', 'password': 'barpass'})
        next_page = '/next'
        ip = '123.45.67.89'

        with self.app.app_context():
            data, code, headers = login('POST', form_data, ip, next_page)
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(data['form'], LoginForm,
                              "Response includes a login form.")

    @mock.patch('accounts.controllers.authentication.legacy_sessions')
    @mock.patch('accounts.controllers.authentication.SessionStore')
    @mock.patch('accounts.controllers.authentication.authenticate')
    def test_post_great(self, mock_authenticate, mock_SessionStore, mock_session):
        """Form data are valid and check out."""
        form_data = MultiDict({'username': 'foouser', 'password': 'bazpass'})
        ip = '123.45.67.89'
        next_page = '/foo'
        start_time = datetime.now(tz=UTC)
        user = domain.User(
            user_id=42,
            username='foouser',
            email='user@ema.il',
            verified=True
        )
        auths = domain.Authorizations(
            classic=6,
            scopes=['public:read', 'submission:create']
        )
        mock_authenticate.return_value = user, auths
        c_session = domain.Session(
            session_id='barsession',
            user=user,
            start_time=start_time,
            authorizations=auths
        )
        c_cookie = 'bardata'
        mock_session.create.return_value = c_session
        mock_session.generate_cookie.return_value = c_cookie
        session = domain.Session(
            session_id='foosession',
            user=user,
            start_time=start_time,
            authorizations=domain.Authorizations(
                scopes=['public:read', 'submission:create']
            )
        )
        cookie = 'foodata'
        mock_SessionStore.current_session.return_value \
            .create.return_value = session
        mock_SessionStore.current_session.return_value \
            .generate_cookie.return_value = cookie

        with self.app.app_context():
            data, status_code, header = login('POST', form_data, ip, next_page)
        self.assertEqual(status_code, status.HTTP_303_SEE_OTHER,
                         "Redirects user to next page")
        self.assertEqual(header['Location'], next_page,
                         "Redirects user to next page.")
        self.assertEqual(data['cookies']['auth_session_cookie'],
                         (cookie, None),
                         "Session cookie is returned")
        self.assertEqual(data['cookies']['classic_cookie'], (c_cookie, None),
                         "Classic session cookie is returned")

    @mock.patch('accounts.controllers.authentication.SessionStore')
    @mock.patch('accounts.controllers.authentication.legacy_sessions')
    @mock.patch('accounts.controllers.authentication.authenticate')
    def test_post_not_verified(self, mock_authenticate, mock_legacy_sess, mock_SessionStore):
        """Form data are valid and check out."""
        form_data = MultiDict({'username': 'foouser', 'password': 'bazpass'})
        ip = '123.45.67.89'
        next_page = '/foo'
        start_time = datetime.now(tz=UTC)
        user = domain.User(
            user_id=42,
            username='foouser',
            email='user@ema.il',
            verified=False
        )
        auths = domain.Authorizations(
            classic=6,
            scopes=['public:read', 'submission:create']
        )
        mock_authenticate.return_value = user, auths
        c_session = domain.Session(
            session_id='barsession',
            user=user,
            start_time=start_time,
            authorizations=auths
        )
        c_cookie = 'bardata'
        mock_legacy_sess.create.return_value = c_session
        mock_legacy_sess.generate_cookie.return_value = c_cookie
        session = domain.Session(
            session_id='foosession',
            user=user,
            start_time=start_time,
            authorizations=domain.Authorizations(
                scopes=['public:read', 'submission:create']
            )
        )
        cookie = 'foodata'
        mock_SessionStore.current_session.return_value \
            .create.return_value = session
        mock_SessionStore.current_session.return_value \
            .generate_cookie.return_value = cookie

        with self.app.app_context():
            data, status_code, header = login('POST', form_data, ip, next_page)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST,
                         "Bad request error is returned")


    @mock.patch('accounts.controllers.authentication.authenticate')
    def testpost_db_unaval(self, mock_authenticate):
        """POST but DB is unavailable.

        arxiv/users/legacy/authenticate.py", line 60, in authenticate
        Raise MySQLdb._exceptions.OperationalError """
        form_data = MultiDict({'username': 'foouser', 'password': 'bazpass'})
        ip = '123.45.67.89'
        next_page = '/foo'

        import MySQLdb
        def rasie_db_op_err(*a, **k):
            raise MySQLdb._exceptions.OperationalError(f"This is a mocked exceptions in {__file__}")
        mock_authenticate.side_effect = rasie_db_op_err

        with self.app.app_context():
            data, status_code, header = login('POST', form_data, ip, next_page)
        self.assertNotEqual(status_code, status.HTTP_303_SEE_OTHER, "should not login if db is down")
