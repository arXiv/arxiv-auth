"""Integration tests for the session_store session store with Redis."""

from unittest import TestCase
import subprocess
import time
import json

import os
import redis
import jwt

from accounts.services import session_store
from accounts.services.exceptions import *
from accounts.domain import UserSession, User, UserPrivileges


class TestDistributedSessionServiceIntegration(TestCase):
    """Test integration with Redis."""

    @classmethod
    def setUpClass(cls):
        """Spin up redis."""
        cls.redis = subprocess.run(
            "docker run -d -p 6379:6379 redis",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        if cls.redis.returncode > 0:
            raise RuntimeError('Could not start redis. Is Docker running?')
        cls.container = cls.redis.stdout.decode('ascii').strip()
        cls.secret = 'bazsecret'
        os.environ['JWT_SECRET'] = cls.secret
        time.sleep(5)    # In case it takes a moment to start.

    @classmethod
    def tearDownClass(cls):
        """Tear down redis."""
        subprocess.run(f"docker rm -f {cls.container}",
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       shell=True)

    def test_create_user_session(self):
        """An entry should be created in Redis."""

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
        session = session_store.create_user_session(user, ip, remote_host)

        # API still works as expected.
        self.assertIsInstance(session, UserSession)
        self.assertTrue(bool(session.session_id))
        self.assertIsNotNone(session.cookie)

        # Are the expected values stored in Redis?
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        raw = r.get(session.session_id)
        stored_data = json.loads(raw)
        cookie_data = jwt.decode(session.cookie, self.secret)
        self.assertEqual(stored_data['nonce'], cookie_data['nonce'])

    def test_get_user_session(self):
        """Get a session from the datastore."""
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        data_in = {'user_id': 42}
        r.set('fookey', json.dumps(data_in))
        data_out = session_store.get_user_session('fookey')
        self.assertIsNotNone(data_out)
        self.assertEqual(42, data_out['user_id'])

    def test_invalidate_session(self):
        """Invalidate a session from the datastore."""
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        data_in = {'end_time': time.time() + 30 * 60, 'user_id': 1,
                   'nonce': '123'}
        r.set('fookey', json.dumps(data_in))
        data0 = json.loads(r.get('fookey'))
        now = time.time()
        self.assertGreaterEqual(data0['end_time'], now)
        session_store.invalidate_user_session(
            session_store.current_session()._pack_cookie({
                'session_id': 'fookey',
                'nonce': '123',
                'user_id': 1
            })
        )
        data1 = json.loads(r.get('fookey'))
        now = time.time()
        self.assertGreaterEqual(now, data1['end_time'])

    def test_delete_session(self):
        """Delete a session from the datastore."""
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        r.set('fookey', b'foovalue')
        session_store.delete_user_session('fookey')
