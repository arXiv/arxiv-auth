"""Integration tests for the session_store session store with Redis."""

from unittest import TestCase, mock
import subprocess
import time
import json

import os
import redis
import rediscluster
import jwt

from .... import domain
from .. import store


class TestDistributedSessionServiceIntegration(TestCase):
    """Test integration with Redis."""

    __test__ = int(bool(os.environ.get('WITH_INTEGRATION', False)))

    @classmethod
    def setUpClass(self):
        """Spin up redis."""
        # self.redis = subprocess.run(
        #     "docker run -d -p 7000:7000 -p 7001:7001 -p 7002:7002 -p 7003:7003"
        #     " -p 7004:7004 -p 7005:7005 -p 7006:7006 -e \"IP=0.0.0.0\""
        #     " --hostname=server grokzen/redis-cluster:4.0.9",
        #     stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        # )
        # if self.redis.returncode > 0:
        #     raise RuntimeError('Could not start redis. Is Docker running?')
        # self.container = self.redis.stdout.decode('ascii').strip()
        self.secret = 'bazsecret'
        # time.sleep(10)    # In case it takes a moment to start.

    @classmethod
    def tearDownClass(self):
        """Tear down redis."""
        # subprocess.run(f"docker rm -f {self.container}",
        #                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        #                shell=True)

    @mock.patch(f'{store.__name__}.get_application_config')
    def test_store_create(self, mock_get_config):
        """An entry should be created in Redis."""
        mock_get_config.return_value = {'JWT_SECRET': self.secret}
        ip = '127.0.0.1'
        remote_host = 'foo-host.foo.com'
        user = domain.User(
            user_id='1',
            username='theuser',
            email='the@user.com',
        )
        authorizations = domain.Authorizations(
            classic=2,
            scopes=['foo:write'],
            endorsements=[]
        )
        session = store.create(authorizations, ip, remote_host, user=user)
        cookie = store.generate_cookie(session)

        # API still works as expected.
        self.assertIsInstance(session, domain.Session)
        self.assertTrue(bool(session.session_id))
        self.assertIsNotNone(cookie)

        # Are the expected values stored in Redis?
        r = rediscluster.StrictRedisCluster(startup_nodes=[dict(host='localhost', port='7000')])
        raw = r.get(session.session_id)
        stored_data = json.loads(raw)
        cookie_data = jwt.decode(cookie, self.secret)
        self.assertEqual(stored_data['nonce'], cookie_data['nonce'])

    # def test_invalidate_session(self):
    #     """Invalidate a session from the datastore."""
    #     r = rediscluster.StrictRedisCluster(startup_nodes=[dict(host='localhost', port='7000')])
    #     data_in = {'end_time': time.time() + 30 * 60, 'user_id': 1,
    #                'nonce': '123'}
    #     r.set('fookey', json.dumps(data_in))
    #     data0 = json.loads(r.get('fookey'))
    #     now = time.time()
    #     self.assertGreaterEqual(data0['end_time'], now)
    #     store.invalidate(
    #         store.current_session()._pack_cookie({
    #             'session_id': 'fookey',
    #             'nonce': '123',
    #             'user_id': 1
    #         })
    #     )
    #     data1 = json.loads(r.get('fookey'))
    #     now = time.time()
    #     self.assertGreaterEqual(now, data1['end_time'])

    @mock.patch(f'{store.__name__}.get_application_config')
    def test_delete_session(self, mock_get_config):
        """Delete a session from the datastore."""
        mock_get_config.return_value = {'JWT_SECRET': self.secret}
        r = rediscluster.StrictRedisCluster(startup_nodes=[dict(host='localhost', port='7000')])
        r.set('fookey', b'foovalue')
        store.delete_by_id('fookey')
