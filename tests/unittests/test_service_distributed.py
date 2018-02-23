from unittest import TestCase, mock
import time
from redis.exceptions import ConnectionError

from accounts.services import distributed
from accounts.domain import SessionData, UserData


class TestDistributedSessionService(TestCase):
    """The distributed session service mints sessions in a key-value store."""

    @mock.patch('accounts.services.distributed.redis')
    def test_create_session(self, mock_redis):
        """Accept a :class:`.UserData` and returns a :class:`.SessionData`."""
        mock_redis_connection = mock.MagicMock()
        mock_redis.StrictRedis.return_value = mock_redis_connection

        user_data = UserData(
            user_id=1,
            start_time=time.time(),
            end_time=time.time() + 30*60*1000,
            last_reissue=0,
            ip_address='127.0.0.1',
            remote_host='foo-host.foo.com',
            user_name='theuser',
            user_email='the@user.com',
            scopes=['foo:write']
        )
        r = distributed.RedisSession('localhost', 6379, 0)
        session = r.create_session(user_data)
        self.assertIsInstance(session, SessionData)
        self.assertTrue(bool(session.session_id))
        self.assertTrue(bool(session.data))
        self.assertEqual(mock_redis_connection.set.call_count, 1)

    @mock.patch('accounts.services.distributed.redis')
    def test_delete_session(self, mock_redis):
        """Delete a session from the datastore."""
        mock_redis_connection = mock.MagicMock()
        mock_redis.StrictRedis.return_value = mock_redis_connection
        r = distributed.RedisSession('localhost', 6379, 0)
        r.delete_session('fookey')
        self.assertEqual(mock_redis_connection.delete.call_count, 1)

    @mock.patch('accounts.services.distributed.redis')
    def test_connection_failed(self, mock_redis):
        """:class:`.SessionCreationFailed` is raised when creation fails."""
        mock_redis.exceptions.ConnectionError = ConnectionError
        mock_redis_connection = mock.MagicMock()
        mock_redis_connection.set.side_effect = ConnectionError
        mock_redis.StrictRedis.return_value = mock_redis_connection
        user_data = UserData(
            user_id=1,
            start_time=time.time(),
            end_time=time.time() + 30*60*1000,
            last_reissue=0,
            ip_address='127.0.0.1',
            remote_host='foo-host.foo.com',
            user_name='theuser',
            user_email='the@user.com',
            scopes=['foo:write']
        )
        r = distributed.RedisSession('localhost', 6379, 0)
        with self.assertRaises(distributed.SessionCreationFailed):
            r.create_session(user_data)
