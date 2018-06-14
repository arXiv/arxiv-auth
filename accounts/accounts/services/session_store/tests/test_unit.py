from unittest import TestCase, mock
import time
from redis.exceptions import ConnectionError

from accounts.services import session_store
from accounts.domain import UserSession, User, UserPrivileges


class TestDistributedSessionService(TestCase):
    """The session_store session service mints sessions in a key-value store."""

    @mock.patch('accounts.services.session_store.redis')
    def test_create_user_session(self, mock_redis):
        """Accept a :class:`.User` and returns a :class:`.UserSession`."""
        mock_redis_connection = mock.MagicMock()
        mock_redis.StrictRedis.return_value = mock_redis_connection
        ip = '127.0.0.1'
        remote_host = 'foo-host.foo.com'
        user = User(
            user_id=1,
            username='theuser',
            email='the@user.com',
            privileges=UserPrivileges(
                classic=2,
                scopes=['foo:write'],
                endorsement_domains=[]
            )
        )
        r = session_store.RedisSession('localhost', 6379, 0, 'foosecret')
        session = r.create_user_session(user, ip, remote_host)
        self.assertIsInstance(session, UserSession)
        self.assertTrue(bool(session.session_id))
        self.assertIsNotNone(session.cookie)
        self.assertEqual(mock_redis_connection.set.call_count, 1)

    @mock.patch('accounts.services.session_store.redis')
    def test_delete_user_session(self, mock_redis):
        """Delete a session from the datastore."""
        mock_redis_connection = mock.MagicMock()
        mock_redis.StrictRedis.return_value = mock_redis_connection
        r = session_store.RedisSession('localhost', 6379, 0, 'foosecret')
        r.delete_user_session('fookey')
        self.assertEqual(mock_redis_connection.delete.call_count, 1)

    @mock.patch('accounts.services.session_store.redis')
    def test_connection_failed(self, mock_redis):
        """:class:`.SessionCreationFailed` is raised when creation fails."""
        mock_redis.exceptions.ConnectionError = ConnectionError
        mock_redis_connection = mock.MagicMock()
        mock_redis_connection.set.side_effect = ConnectionError
        mock_redis.StrictRedis.return_value = mock_redis_connection
        ip = '127.0.0.1'
        remote_host = 'foo-host.foo.com'
        user = User(
            user_id=1,
            username='theuser',
            email='the@user.com',
            privileges=UserPrivileges(
                classic=2,
                scopes=['foo:write'],
                endorsement_domains=[]
            )
        )
        r = session_store.RedisSession('localhost', 6379, 0, 'foosecret')
        with self.assertRaises(session_store.SessionCreationFailed):
            r.create_user_session(user, ip, remote_host)
