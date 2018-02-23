"""Integration tests for the distributed session store with Redis."""

from unittest import TestCase
import subprocess
from accounts.services import distributed
from accounts.domain import SessionData, UserData
import time
import redis
import json
import jwt


class TestDistributedSessionServiceIntegration(TestCase):
    """Test integration with Redis."""

    @classmethod
    def setUpClass(cls):
        """Spin up redis."""
        cls.redis = subprocess.run(
            "docker run -d -p 6379:6379 redis",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        cls.container = cls.redis.stdout.decode('ascii').strip()
        time.sleep(5)    # In case it takes a moment to start.

    @classmethod
    def tearDownClass(cls):
        """Tear down redis."""
        subprocess.run(f"docker rm -f {cls.container}",
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       shell=True)

    def test_create_session(self):
        """An entry should be created in Redis."""
        user_data = UserData(
            user_id=1,
            start_time=time.time(),
            end_time=time.time() + 30*60*1000,
            last_reissue=0,
            ip_address='127.0.0.1',
            remote_host='foo-host.foo.com',
            tracking_cookie='4cbb1ae93066982df8a016277b245e65fa726afa',
            user_name='theuser',
            user_email='the@user.com',
            scopes=['foo:write']
        )
        session = distributed.create_session(user_data)

        # API still works as expected.
        self.assertIsInstance(session, SessionData)
        self.assertTrue(bool(session.session_id))
        self.assertTrue(bool(session.data))

        # Are the expected values stored in Redis?
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        raw = r.get(session.session_id)
        stored_data = json.loads(raw)
        self.assertEqual(user_data.end_time, stored_data['end_time'])
        self.assertDictEqual(user_data._asdict(), stored_data)
