"""Tests for mod:`accounts.controllers`."""

from unittest import TestCase, mock
from datetime import datetime as dt

from werkzeug import MultiDict
from werkzeug.exceptions import BadRequest

from arxiv import status
from accounts.services import exceptions, users
from accounts.domain import User, UserSession, UserPrivileges
from accounts.controllers import get_login, post_login, logout, forms


def raise_authentication_failed(*args, **kwargs):
    """Simulate a failed login attempt at the backend service."""
    raise users.AuthenticationFailed('nope')


class TestLogout(TestCase):
    """Tests for :func:`.logout`."""

    @mock.patch('accounts.controllers.sessions')
    @mock.patch('accounts.controllers.classic')
    def test_logout(self, mock_classic, mock_session_store):
        """A logged-in user requests to log out."""
        mock_classic.invalidate_session.return_value = None
        mock_session_store.invalidate_session.return_value = None
        next_page = '/'
        session_id = 'foosession'
        classic_id = 'bazsession'
        data, status_code, header = logout(session_id, classic_id, next_page)
        self.assertEqual(status_code, status.HTTP_303_SEE_OTHER,
                         "Redirects user to next page")
        self.assertEqual(header['Location'], next_page,
                         "Redirects user to next page.")

    @mock.patch('accounts.controllers.sessions')
    @mock.patch('accounts.controllers.classic')
    def test_logout_anonymous(self, mock_classic, mock_session_store):
        """An anonymous user requests to log out."""
        mock_classic.invalidate_session.return_value = None
        mock_session_store.invalidate_session.return_value = None
        next_page = '/'
        data, status_code, header = logout(None, None, next_page)
        self.assertEqual(status_code, status.HTTP_303_SEE_OTHER,
                         "Redirects user to next page")
        self.assertEqual(header['Location'], next_page,
                         "Redirects user to next page.")


class TestGETLogin(TestCase):
    """Tests for :func:`.get_login`."""

    def test_get_login(self):
        """User requests the login page."""
        data, status_code, header = get_login()
        self.assertIn('form', data)
        self.assertIsInstance(data['form'], forms.LoginForm,
                              "Response includes a login form.")
        self.assertEqual(status_code, status.HTTP_200_OK)


class TestPOSTLogin(TestCase):
    """Tests for func:`.post_login`."""

    def test_post_invalid_data(self):
        """User submits invalid data."""
        form_data = MultiDict({'username': 'foouser'})     # Missing password.
        next_page = '/next'
        ip = '123.45.67.89'
        data, status_code, header = post_login(form_data, ip, next_page)
        self.assertIn('form', data)
        self.assertIsInstance(data['form'], forms.LoginForm,
                              "Response includes a login form.")
        self.assertGreater(len(data['form'].password.errors), 0,
                           "Password field has an error")
        self.assertEqual(status_code, status.HTTP_200_OK,
                         "Response status is OK")

    @mock.patch('accounts.controllers.users')
    @mock.patch('accounts.controllers.classic')
    def test_post_valid_data_bad_credentials(self, mock_classic, mock_users):
        """Form data are valid but don't check out."""
        mock_users.AuthenticationFailed = users.AuthenticationFailed
        mock_users.authenticate.side_effect = raise_authentication_failed

        form_data = MultiDict({'username': 'foouser', 'password': 'barpass'})
        next_page = '/next'
        ip = '123.45.67.89'
        with self.assertRaises(BadRequest):
            post_login(form_data, ip, next_page)

    @mock.patch('accounts.controllers.users')
    @mock.patch('accounts.controllers.sessions')
    @mock.patch('accounts.controllers.classic')
    def test_post_great(self, mock_classic, mock_session_store, mock_users):
        """Form data are valid and check out."""
        mock_users.AuthenticationFailed = users.AuthenticationFailed
        form_data = MultiDict({'username': 'foouser', 'password': 'bazpass'})
        ip = '123.45.67.89'
        next_page = '/foo'
        start_time = (dt.now() - dt.utcfromtimestamp(0)).total_seconds()
        user = User(
            user_id=42,
            username='foouser',
            email='user@ema.il',
            privileges=UserPrivileges(
                classic=6,
                scopes=['public:read', 'submission:create']
            )
        )
        mock_users.authenticate.return_value = user
        classic_session = UserSession(
            session_id='barsession',
            cookie=b'bardata',
            user=user,
            start_time=start_time
        )
        mock_classic.create_user_session.return_value = classic_session
        session = UserSession(
            session_id='foosession',
            cookie=b'foodata',
            user=user,
            start_time=start_time
        )
        mock_session_store.create_user_session.return_value = session

        data, status_code, header = post_login(form_data, ip, next_page)
        self.assertEqual(status_code, status.HTTP_303_SEE_OTHER,
                         "Redirects user to next page")
        self.assertEqual(header['Location'], next_page,
                         "Redirects user to next page.")
        self.assertEqual(data['session_cookie'], session.cookie,
                         "Session cookie is returned")
        self.assertEqual(data['classic_cookie'],
                         classic_session.cookie,
                         "Classic session cookie is returned")
