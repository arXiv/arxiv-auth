"""API tests for the authorizer service."""

from unittest import TestCase, mock
import json
from datetime import datetime
import jwt

from arxiv import status
from authorizer.factory import create_app


class TestAuthorizeWithCookie(TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['SESSION_COOKIE_NAME'] = 'foocookie'
        self.app.config['REDIS_HOST'] = 'redis'
        self.app.config['REDIS_PORT'] = '1234'
        self.app.config['REDIS_DATABASE'] = 4
        self.client = self.app.test_client()

    def test_no_auth_data(self):
        """Neither an authorization token nor cookie are passed."""
        response = self.client.get('/auth')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_not_a_token(self, mock_get_redis):
        """Something other than a JWT is passed."""
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        self.client.set_cookie('', self.app.config['SESSION_COOKIE_NAME'],
                               'definitelynotatoken')
        response = self.client.get('/auth')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_malformed_token(self, mock_get_redis):
        """A JWT with missing claims is passed."""
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        required_claims = ['session_id', 'user_id', 'nonce']
        for exc in required_claims:
            claims = {claim: '' for claim in required_claims if claim != exc}
            bad_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
                .decode('utf-8')
            self.client.set_cookie('', self.app.config['SESSION_COOKIE_NAME'],
                                   bad_token)
            response = self.client.get('/auth')
            self.assertEqual(response.status_code,
                             status.HTTP_401_UNAUTHORIZED)
            data = json.loads(response.data)
            self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_token_with_bad_encryption(self, mock_get_redis):
        """A JWT produced with a different secret is passed."""
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        bad_token = jwt.encode(claims, 'nottherightsecret')
        self.client.set_cookie('', self.app.config['SESSION_COOKIE_NAME'],
                               bad_token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_expired_token(self, mock_get_redis):
        """A JWT produced with a different secret is passed."""
        now = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099',
            'end_time': now - 60
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        expired_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        self.client.set_cookie('', self.app.config['SESSION_COOKIE_NAME'],
                               expired_token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_forged_token(self, mock_get_redis):
        """A JWT with the wrong nonce is passed."""
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290098'
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'    # <- Doesn't match!
        }
        forged_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        self.client.set_cookie('', self.app.config['SESSION_COOKIE_NAME'],
                               forged_token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_other_forged_token(self, mock_get_redis):
        """A JWT with the wrong user_id is passed."""
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1235',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',  # <- Doesn't match!
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        forged_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        self.client.set_cookie('', self.app.config['SESSION_COOKIE_NAME'],
                               forged_token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_empty_session(self, mock_get_redis):
        """Session has been removed, or may never have existed."""
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = ''    # <- Empty record!
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        self.client.set_cookie('', self.app.config['SESSION_COOKIE_NAME'],
                               token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_valid_token(self, mock_get_redis):
        """A valid token is passed."""
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290098'
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290098'
        }
        token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        self.client.set_cookie('', self.app.config['SESSION_COOKIE_NAME'],
                               token)
        response = self.client.get('/auth')
        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        data = json.loads(response.data)
        self.assertIn('Token', response.headers,
                      'Token header is set in response')
        expected_jwt = jwt.encode(
            {'user_id': '1234', 'session_id': 'ajx9043jjx00s'},
            self.app.config['JWT_SECRET']
        ).decode('utf-8')
        self.assertEqual(response.headers['Token'], expected_jwt)


class TestAuthorizeWithHeader(TestCase):
    """Tests for :func:`session_store.get_token_session`."""

    def setUp(self):
        self.app = create_app()
        self.app.config['SESSION_COOKIE_NAME'] = 'foocookie'
        self.app.config['REDIS_HOST'] = 'redis'
        self.app.config['REDIS_PORT'] = '1234'
        self.app.config['REDIS_DATABASE'] = 4
        self.client = self.app.test_client()

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_not_a_token(self, mock_get_redis):
        """Something other than a JWT is passed."""
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        headers = {'Authorization': 'Bearer notthetokenyouarelookingfor'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_malformed_token(self, mock_get_redis):
        """A JWT with missing claims is passed."""
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        required_claims = ['session_id', 'user_id', 'nonce']
        for exc in required_claims:
            claims = {claim: '' for claim in required_claims if claim != exc}
            bad_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
                .decode('utf-8')
            headers = {'Authorization': f'Bearer {bad_token}'}
            response = self.client.get('/auth', headers=headers)
            self.assertEqual(response.status_code,
                             status.HTTP_401_UNAUTHORIZED)
            data = json.loads(response.data)
            self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_token_with_bad_encryption(self, mock_get_redis):
        """A JWT produced with a different secret is passed."""
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        claims = {
            'user_id': '1234',
            'client_id': '5678',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        bad_token = jwt.encode(claims, 'nottherightsecret')
        headers = {'Authorization': f'Bearer {bad_token}'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_expired_token(self, mock_get_redis):
        """A JWT produced with a different secret is passed."""
        now = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1234',
            'client_id': '5678',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099',
            'end_time': now - 60
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'client_id': '5678',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        expired_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        headers = {'Authorization': f'Bearer {expired_token}'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_forged_token(self, mock_get_redis):
        """A JWT with the wrong nonce is passed."""
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1234',
            'client_id': '5678',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290098'
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'client_id': '5678',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'    # <- Doesn't match!
        }
        bad_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        headers = {'Authorization': f'Bearer {bad_token}'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_other_forged_token(self, mock_get_redis):
        """A JWT with the wrong user_id is passed."""
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1235',
            'client_id': '5678',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',  # <- Doesn't match!
            'client_id': '5678',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        bad_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        headers = {'Authorization': f'Bearer {bad_token}'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_other_other_forged_token(self, mock_get_redis):
        """A JWT with the wrong client_id is passed."""
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1234',
            'client_id': '5678',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'client_id': '5679',     # <- Doesn't match!
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        bad_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        headers = {'Authorization': f'Bearer {bad_token}'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_empty_session(self, mock_get_redis):
        """Session has been removed, or may never have existed."""
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = ''    # <- Empty record!
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'client_id': '5679',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        bad_token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        headers = {'Authorization': f'Bearer {bad_token}'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        data = json.loads(response.data)
        self.assertIn('reason', data, 'Response includes failure reason')

    @mock.patch('authorizer.services.session_store._get_redis')
    def test_valid_token(self, mock_get_redis):
        """A valid token is passed."""
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1234',
            'client_id': '5679',
            'session_id': 'a1234thh',
            'nonce': '0039299290098'
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'client_id': '5679',
            'session_id': 'a1234thh',
            'nonce': '0039299290098'
        }
        token = jwt.encode(claims, self.app.config['JWT_SECRET']) \
            .decode('utf-8')
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.get('/auth', headers=headers)
        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        self.assertIn('Token', response.headers,
                      'Token header is set in response')
        expected_jwt = jwt.encode(
            {'user_id': '1234', 'client_id': '5679', 'session_id': 'a1234thh'},
            self.app.config['JWT_SECRET']
        ).decode('utf-8')
        self.assertEqual(response.headers['Token'], expected_jwt)
