"""End-to-end test for :mod:`registry`."""

import os
import subprocess
import time
import json
from datetime import datetime, timedelta
from hashlib import sha256
from unittest import TestCase

from arxiv import status
from registry.factory import create_web_app
from registry.services import datastore
from registry.domain import Client, ClientGrantType, ClientCredential, \
    ClientAuthorization


def stop_container(container):
    subprocess.run(f"docker rm -f {container}",
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                   shell=True)
    from registry.services import datastore
    datastore.drop_all()


class TestClientAuthentication(TestCase):
    __test__ = int(bool(os.environ.get('WITH_INTEGRATION', False)))

    def setUp(self):
        """Spin up redis."""
        self.redis = subprocess.run(
            "docker run -d -p 6379:6379 redis",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        time.sleep(2)    # In case it takes a moment to start.
        if self.redis.returncode > 0:
            raise RuntimeError('Could not start redis. Is Docker running?')

        self.container = self.redis.stdout.decode('ascii').strip()
        self.db = 'db.sqlite'

        self.client = Client(
            owner_id='252',
            name='fooclient',
            url='http://asdf.com',
            description='a client',
            redirect_uri='https://foo.com/bar'
        )
        self.secret = 'foohashedsecret'
        self.hashed_secret = sha256(self.secret.encode('utf-8')).hexdigest()
        self.cred = ClientCredential(client_secret=self.hashed_secret)
        self.auths = [
            ClientAuthorization(
                scope='foo:bar',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            ),
            ClientAuthorization(
                scope='baz:bat',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            )
        ]
        self.grant_types = [
            ClientGrantType(
                grant_type='client_credentials',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            )
        ]
        try:
            os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'
            self.app = create_web_app()
            self.app.config['REGISTRY_DATABASE_URI'] = f'sqlite:///{self.db}'

            self.test_client = self.app.test_client()
            with self.app.app_context():
                datastore.create_all()
                self.client_id = datastore.save_client(
                    self.client,
                    self.cred,
                    auths=self.auths,
                    grant_types=self.grant_types
                )

        except Exception as e:
            stop_container(self.container)
            raise

    def tearDown(self):
        """Tear down redis."""
        stop_container(self.container)
        os.remove(self.db)

    def test_post_credentials(self):
        """POST request to /token returns auth token."""
        payload = {
            'client_id': self.client_id,
            'client_secret': self.secret,
            'grant_type': 'client_credentials'
        }
        response = self.test_client.post('/token', data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('access_token', json.loads(response.data))
        self.assertIn('expires_in', json.loads(response.data))
        self.assertIn('token_type', json.loads(response.data))

    def test_post_invalid_credentials(self):
        """POST request with bad creds returns 400 Bad Request."""
        payload = {
            'client_id': self.client_id,
            'client_secret': 'not the secret',
            'grant_type': 'client_credentials'
        }
        response = self.test_client.post('/token', data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.data, b'{"error": "invalid_client"}')

    def test_post_invalid_grant_type(self):
        """POST request with bad grant type returns 400 Bad Request."""
        payload = {
            'client_id': self.client_id,
            'client_secret': self.secret,
            'grant_type': 'implicit'
        }
        response = self.test_client.post('/token', data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.data, b'{"error": "invalid_grant"}')

    def test_post_invalid_scope(self):
        """POST request with unauthorized scope returns 400 Bad Request."""
        payload = {
            'client_id': self.client_id,
            'client_secret': self.secret,
            'grant_type': 'client_credentials',
            'scope': 'not:authorized,delete:everything'
        }
        response = self.test_client.post('/token', data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertEqual(data['error'], "invalid_scope")
