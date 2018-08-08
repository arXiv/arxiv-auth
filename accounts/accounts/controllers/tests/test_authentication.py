"""Tests for mod:`accounts.controllers`."""

from unittest import TestCase, mock
from datetime import datetime
from pytz import timezone

from werkzeug import MultiDict
from werkzeug.exceptions import BadRequest

from arxiv import status
from arxiv.users import domain
from accounts.services import legacy, users, sessions
from accounts.controllers.authentication import login, logout, LoginForm


EASTERN = timezone('US/Eastern')


def raise_authentication_failed(*args, **kwargs):
    """Simulate a failed login attempt at the backend service."""
    raise users.exceptions.AuthenticationFailed('nope')


class TestLogout(TestCase):
    """Tests for :func:`.logout`."""

    @mock.patch('accounts.controllers.authentication.sessions')
    @mock.patch('accounts.controllers.authentication.legacy')
    def test_logout(self, mock_legacy, mock_sessions):
        """A logged-in user requests to log out."""
        mock_legacy.sessions.invalidate_session.return_value = None
        mock_sessions.invalidate_session.return_value = None
        next_page = '/'
        session_id = 'foosession'
        classic_id = 'bazsession'
        data, status_code, header = logout(session_id, classic_id, next_page)
        self.assertEqual(status_code, status.HTTP_303_SEE_OTHER,
                         "Redirects user to next page")
        self.assertEqual(header['Location'], next_page,
                         "Redirects user to next page.")

    @mock.patch('accounts.controllers.authentication.sessions')
    @mock.patch('accounts.controllers.authentication.legacy')
    def test_logout_anonymous(self, mock_legacy, mock_sessions):
        """An anonymous user requests to log out."""
        mock_legacy.sessions.invalidate_session.return_value = None
        mock_sessions.invalidate_session.return_value = None
        next_page = '/'
        data, status_code, header = logout(None, None, next_page)
        self.assertEqual(status_code, status.HTTP_303_SEE_OTHER,
                         "Redirects user to next page")
        self.assertEqual(header['Location'], next_page,
                         "Redirects user to next page.")


class TestGETLogin(TestCase):
    """Tests for :func:`.login`."""

    def test_login(self):
        """User requests the login page."""
        data, status_code, header = login('GET', {}, '', '')
        self.assertIn('form', data)
        self.assertIsInstance(data['form'], LoginForm,
                              "Response includes a login form.")
        self.assertEqual(status_code, status.HTTP_200_OK)


class TestPOSTLogin(TestCase):
    """Tests for func:`.login`."""

    def test_post_invalid_data(self):
        """User submits invalid data."""
        form_data = MultiDict({'username': 'foouser'})     # Missing password.
        next_page = '/next'
        ip = '123.45.67.89'
        data, status_code, header = login('POST', form_data, ip, next_page)
        self.assertIn('form', data)
        self.assertIsInstance(data['form'], LoginForm,
                              "Response includes a login form.")
        self.assertGreater(len(data['form'].password.errors), 0,
                           "Password field has an error")
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST,
                         "Response status is 400 bad request")

    @mock.patch('accounts.controllers.authentication.users')
    @mock.patch('accounts.controllers.authentication.legacy')
    def test_post_valid_data_bad_credentials(self, mock_legacy, mock_users):
        """Form data are valid but don't check out."""
        mock_users.exceptions.AuthenticationFailed = \
            users.exceptions.AuthenticationFailed
        mock_legacy.exceptions.SessionCreationFailed = \
            legacy.exceptions.SessionCreationFailed
        mock_users.authenticate.side_effect = raise_authentication_failed

        form_data = MultiDict({'username': 'foouser', 'password': 'barpass'})
        next_page = '/next'
        ip = '123.45.67.89'

        data, code, headers = login('POST', form_data, ip, next_page)
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(data['form'], LoginForm,
                              "Response includes a login form.")

    @mock.patch('accounts.controllers.authentication.users')
    @mock.patch('accounts.controllers.authentication.sessions')
    @mock.patch('accounts.controllers.authentication.legacy')
    def test_post_great(self, mock_legacy, mock_sessions, mock_users):
        """Form data are valid and check out."""
        mock_users.exceptions.AuthenticationFailed = \
            users.exceptions.AuthenticationFailed
        mock_sessions.exceptions.SessionCreationFailed = \
            sessions.exceptions.SessionCreationFailed
        mock_legacy.exceptions.SessionCreationFailed = \
            legacy.exceptions.SessionCreationFailed
        form_data = MultiDict({'username': 'foouser', 'password': 'bazpass'})
        ip = '123.45.67.89'
        next_page = '/foo'
        start_time = datetime.now(tz=EASTERN)
        user = domain.User(
            user_id=42,
            username='foouser',
            email='user@ema.il'
        )
        auths = domain.Authorizations(
            classic=6,
            scopes=['public:read', 'submission:create']
        )
        mock_users.authenticate.return_value = user, auths
        c_session = domain.Session(
            session_id='barsession',
            user=user,
            start_time=start_time,
            authorizations=auths
        )
        c_cookie = 'bardata'
        mock_legacy.create.return_value = c_session
        mock_legacy.generate_cookie.return_value = c_cookie
        session = domain.Session(
            session_id='foosession',
            user=user,
            start_time=start_time,
            authorizations=domain.Authorizations(
                scopes=['public:read', 'submission:create']
            )
        )
        cookie = 'foodata'
        mock_sessions.create.return_value = session
        mock_sessions.generate_cookie.return_value = cookie

        data, status_code, header = login('POST', form_data, ip, next_page)
        self.assertEqual(status_code, status.HTTP_303_SEE_OTHER,
                         "Redirects user to next page")
        self.assertEqual(header['Location'], next_page,
                         "Redirects user to next page.")
        self.assertEqual(data['cookies']['session_cookie'], (cookie, None),
                         "Session cookie is returned")
        self.assertEqual(data['cookies']['classic_cookie'], (c_cookie, None),
                         "Classic session cookie is returned")
