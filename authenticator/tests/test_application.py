"""API tests for the authenticator service."""

from unittest import TestCase, mock
import json
from datetime import datetime, timedelta
from pytz import timezone
import jwt

import arxiv.users.auth.sessions.store
from arxiv import status
from authenticator.factory import create_app

EASTERN = timezone('US/Eastern')

#
class TestAuthorizeWithCookie(TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['AUTH_SESSION_COOKIE_NAME'] = 'foocookie'
        self.app.config['REDIS_CLUSTER'] = '0'
        self.client = self.app.test_client()

    def test_no_auth_data(self):
        """Neither an authorization token nor cookie are passed."""
        response = self.client.get('/auth')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch('authenticator.services.sessions')
    def test_not_a_token(self, mock_sessions):
        """Something other than a JWT is passed."""
        self.client.set_cookie('', self.app.config['AUTH_SESSION_COOKIE_NAME'],
                               'definitelynotatoken')
        response = self.client.get('/auth')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('authenticator.services.sessions')
    def test_malformed_token(self, mock_sessions):
        """A cookie with missing claims is passed."""
        required_claims = ['session_id', 'user_id', 'nonce']
        for exc in required_claims:
            claims = {claim: '' for claim in required_claims if claim != exc}
            bad_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
                .decode('utf-8')
            self.client.set_cookie('', self.app.config['AUTH_SESSION_COOKIE_NAME'],
                                   bad_token)
            response = self.client.get('/auth')
            self.assertEqual(response.status_code,
                             status.HTTP_401_UNAUTHORIZED)
            data = json.loads(response.data)
            self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authenticator.services.sessions')
    def test_token_with_bad_encryption(self, mock_sessions):
        """A cookie produced with a different secret is passed."""
        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        bad_token = jwt.encode(claims, 'nottherightsecret')
        self.client.set_cookie('', self.app.config['AUTH_SESSION_COOKIE_NAME'],
                               bad_token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authenticator.services.sessions.load')
    def test_expired_token(self, mock_load):
        """The session is expired."""
        mock_load.side_effect = arxiv.users.auth.sessions.store.ExpiredToken
        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        expired_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        self.client.set_cookie('', self.app.config['AUTH_SESSION_COOKIE_NAME'],
                               expired_token)
        response = self.client.get('/auth')
        print(response.data)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authenticator.services.sessions.load')
    def test_other_forged_token(self, mock_load):
        """An invalid cookie is passed."""
        mock_load.side_effect = arxiv.users.auth.sessions.store.InvalidToken
        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        forged_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        self.client.set_cookie('', self.app.config['AUTH_SESSION_COOKIE_NAME'],
                               forged_token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authenticator.services.sessions.load')
    def test_empty_session(self, mock_load):
        """Session has been removed, or may never have existed."""
        mock_load.side_effect = arxiv.users.auth.sessions.store.UnknownSession
        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        self.client.set_cookie('', self.app.config['AUTH_SESSION_COOKIE_NAME'],
                               token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authenticator.services.sessions.load')
    def test_valid_token(self, mock_load):
        """A valid cookie is passed."""
        session = arxiv.users.domain.Session(
            user=arxiv.users.domain.User(
                user_id='1234',
                username='foouser',
                email='foo@bar.com'
            ),
            start_time=datetime.now().isoformat(),
            session_id='ajx9043jjx00s',
            nonce='0039299290098'
        )
        mock_load.return_value = jwt.encode(
            arxiv.users.domain.to_dict(session),
            self.app.config['JWT_SECRET']
        )
        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290098'
        }
        token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        self.client.set_cookie('', self.app.config['AUTH_SESSION_COOKIE_NAME'],
                               token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        self.assertIn('Authorization', response.headers,
                      'Authorization header is set in response')
        expected_jwt = jwt.encode(
            arxiv.users.domain.to_dict(session),
            self.app.config['JWT_SECRET']
        ).decode('utf-8')
        self.assertEqual(response.headers['Authorization'], expected_jwt)


class TestAuthorizeWithHeader(TestCase):
    """Tests for :func:`session_store.get_token_session`."""

    def setUp(self):
        """Instantiate the authenticator app for testing."""
        self.app = create_app()
        self.app.config['AUTH_SESSION_COOKIE_NAME'] = 'foocookie'
        self.client = self.app.test_client()

    @mock.patch('authenticator.services.sessions.load_by_id')
    def test_not_a_token(self, mock_load):
        """Something other than a token is passed."""
        mock_load.side_effect = arxiv.users.auth.sessions.store.UnknownSession
        headers = {'Authorization': 'Bearer notthetokenyouarelookingfor'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authenticator.services.sessions.load_by_id')
    def test_expired_token(self, mock_load):
        """An expired token is passed."""
        mock_load.side_effect = arxiv.users.auth.sessions.store.ExpiredToken
        headers = {'Authorization': 'Bearer foo'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authenticator.services.sessions.load_by_id')
    def test_invalid_token(self, mock_load):
        """An invalid token is passed."""
        mock_load.side_effect = arxiv.users.auth.sessions.store.InvalidToken
        headers = {'Authorization': 'Bearer foo'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authenticator.services.sessions.load_by_id')
    def test_valid_token(self, mock_load):
        """A valid token is passed."""
        session = arxiv.users.domain.Session(
            user=arxiv.users.domain.User(
                user_id='1234',
                username='foouser',
                email='foo@bar.com'
            ),
            start_time=datetime.now().isoformat(),
            session_id='foo',
            nonce='0039299290098'
        )
        mock_load.return_value = jwt.encode(
            arxiv.users.domain.to_dict(session),
            self.app.config['JWT_SECRET']
        )
        headers = {'Authorization': 'Bearer foo'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        self.assertIn('Authorization', response.headers,
                      'Authorization header is set in response')
        expected_jwt = jwt.encode(
            arxiv.users.domain.to_dict(session),
            self.app.config['JWT_SECRET']
        ).decode('utf-8')
        self.assertEqual(response.headers['Authorization'], expected_jwt)
