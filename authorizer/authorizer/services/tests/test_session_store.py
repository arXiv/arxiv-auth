from unittest import TestCase, mock
from datetime import datetime
import json
import jwt

from authorizer.services import session_store


class TestGetUserSession(TestCase):
    """Tests for :func:`session_store.get_user_session`."""

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_not_a_token(self, mock_get_redis, mock_app):
        """Something other than a JWT is passed."""
        mock_app.config = {
            'JWT_SECRET': 'barsecret',
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_user_session('notatoken')

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_malformed_token(self, mock_get_redis, mock_app):
        """A JWT with missing claims is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        required_claims = ['session_id', 'user_id', 'nonce']
        for exc in required_claims:
            claims = {claim: '' for claim in required_claims if claim != exc}
            malformed_token = jwt.encode(claims, secret)
            with self.assertRaises(session_store.InvalidToken):
                session_store.get_user_session(malformed_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_token_with_bad_encryption(self, mock_get_redis, mock_app):
        """A JWT produced with a different secret is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        bad_token = jwt.encode(claims, 'nottherightsecret')
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_user_session(bad_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_expired_token(self, mock_get_redis, mock_app):
        """A JWT produced with a different secret is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
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
        expired_token = jwt.encode(claims, secret)
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_user_session(expired_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_forged_token(self, mock_get_redis, mock_app):
        """A JWT with the wrong nonce is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
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
        expired_token = jwt.encode(claims, secret)
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_user_session(expired_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_other_forged_token(self, mock_get_redis, mock_app):
        """A JWT with the wrong user_id is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
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
        expired_token = jwt.encode(claims, secret)
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_user_session(expired_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_empty_session(self, mock_get_redis, mock_app):
        """Session has been removed, or may never have existed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = ''    # <- Empty record!
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        expired_token = jwt.encode(claims, secret)
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_user_session(expired_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_valid_token(self, mock_get_redis, mock_app):
        """A valid token is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
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
        expired_token = jwt.encode(claims, secret)

        claims = session_store.get_user_session(expired_token)
        self.assertIsInstance(claims, dict, "Returns a dict of claims")
        self.assertNotIn("nonce", claims, "Nonce is removed")


class TestGetTokenSession(TestCase):
    """Tests for :func:`session_store.get_token_session`."""

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_not_a_token(self, mock_get_redis, mock_app):
        """Something other than a JWT is passed."""
        mock_app.config = {
            'JWT_SECRET': 'barsecret',
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_token_session('notatoken')

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_malformed_token(self, mock_get_redis, mock_app):
        """A JWT with missing claims is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        required_claims = ['session_id', 'user_id', 'nonce']
        for exc in required_claims:
            claims = {claim: '' for claim in required_claims if claim != exc}
            malformed_token = jwt.encode(claims, secret)
            with self.assertRaises(session_store.InvalidToken):
                session_store.get_token_session(malformed_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_token_with_bad_encryption(self, mock_get_redis, mock_app):
        """A JWT produced with a different secret is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        mock_redis = mock.MagicMock()
        mock_get_redis.return_value = mock_redis
        claims = {
            'user_id': '1234',
            'client_id': '5678',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        bad_token = jwt.encode(claims, 'nottherightsecret')
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_token_session(bad_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_expired_token(self, mock_get_redis, mock_app):
        """A JWT produced with a different secret is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
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
        expired_token = jwt.encode(claims, secret)
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_token_session(expired_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_forged_token(self, mock_get_redis, mock_app):
        """A JWT with the wrong nonce is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
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
        expired_token = jwt.encode(claims, secret)
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_token_session(expired_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_other_forged_token(self, mock_get_redis, mock_app):
        """A JWT with the wrong user_id is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
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
        expired_token = jwt.encode(claims, secret)
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_token_session(expired_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_other_other_forged_token(self, mock_get_redis, mock_app):
        """A JWT with the wrong client_id is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
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
        expired_token = jwt.encode(claims, secret)
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_token_session(expired_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_empty_session(self, mock_get_redis, mock_app):
        """Session has been removed, or may never have existed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = ''    # <- Empty record!
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'client_id': '5679',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290099'
        }
        expired_token = jwt.encode(claims, secret)
        with self.assertRaises(session_store.InvalidToken):
            session_store.get_token_session(expired_token)

    @mock.patch('authorizer.services.session_store.current_app')
    @mock.patch('authorizer.services.session_store._get_redis')
    def test_valid_token(self, mock_get_redis, mock_app):
        """A valid token is passed."""
        secret = 'barsecret'
        mock_app.config = {
            'JWT_SECRET': secret,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        mock_redis = mock.MagicMock()
        mock_redis.get.return_value = json.dumps({
            'user_id': '1234',
            'client_id': '5679',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290098'
        })
        mock_get_redis.return_value = mock_redis

        claims = {
            'user_id': '1234',
            'client_id': '5679',
            'session_id': 'ajx9043jjx00s',
            'nonce': '0039299290098'
        }
        expired_token = jwt.encode(claims, secret)

        claims = session_store.get_user_session(expired_token)
        self.assertIsInstance(claims, dict, "Returns a dict of claims")
        self.assertNotIn("nonce", claims, "Nonce is removed")


class TestGetRedis(TestCase):
    """Tests for private :func:`session_store._get_redis`."""

    @mock.patch('authorizer.services.session_store.current_app')
    def test_app_not_configured(self, mock_app):
        """Required config params are missing."""
        required = ['REDIS_HOST', 'REDIS_PORT', 'REDIS_DATABASE']
        for exc in required:
            mock_app.config = {k: 'foo' for k in required if k != exc}
            with self.assertRaises(session_store.ConfigurationError):
                session_store._get_redis()

    @mock.patch('authorizer.services.session_store.current_app')
    def test_app_configured(self, mock_app):
        """App is configured properly."""
        import redis
        mock_app.config = {
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '1234',
            'REDIS_DATABASE': 4
        }
        r = session_store._get_redis()
        self.assertIsInstance(r, redis.StrictRedis,
                              "A StrictRedis object is returned")
