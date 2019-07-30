"""Tests for :mod:`registry.oauth2`."""

from hashlib import sha256
from datetime import datetime, timedelta
from unittest import TestCase, mock

from ..domain import Client, ClientCredential, ClientAuthorization, \
    ClientGrantType, Session, User, Scope, Authorizations

from ..services import datastore
from .. import oauth2


class TestOAuth2Client(TestCase):
    """Tests for :class:`oauth2.OAuth2Client`."""

    def setUp(self):
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
                grant_type='implicit',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            ),
            ClientGrantType(
                grant_type='password',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            )
        ]

        self.oa2client = oauth2.OAuth2Client(
            self.client, self.cred, self.auths, self.grant_types
        )

    def test_scopes(self):
        """Property :attr:`.scopes` is a list of scopes."""
        self.assertEqual(sorted(self.oa2client.scopes),
                         sorted(['foo:bar', 'baz:bat']))

    def test_check_client_secret(self):
        """Method :meth:`.check_client_secret` evaluates secret."""
        self.assertTrue(self.oa2client.check_client_secret(self.secret))
        self.assertFalse(self.oa2client.check_client_secret('nope'))

    def test_check_grant_type(self):
        """:meth:`.check_grant_type` evaluates authorized grant types."""
        self.assertTrue(self.oa2client.check_grant_type('implicit'))
        self.assertTrue(self.oa2client.check_grant_type('password'))
        self.assertFalse(self.oa2client.check_grant_type('client_credentials'))

    def test_check_redirect_uri(self):
        """:meth:`.check_redirect_uri` evaluates redirect URI."""
        self.assertTrue(
            self.oa2client.check_redirect_uri('https://foo.com/bar')
        )
        self.assertFalse(
            self.oa2client.check_redirect_uri('https://fdsa.com/nope')
        )

    @mock.patch(f'{oauth2.__name__}.request')
    def test_check_requested_scopes(self, mock_request):
        """:meth:`.check_requested_scopes` evaluates authorized scopes."""
        mock_request.auth = Session(
            session_id='1234-abcd',
            start_time=datetime.now(),
            user=User(
                username='foouser',
                email='foo@bar.com',
                user_id='12345'
            ),
            authorizations=Authorizations(
                scopes=[Scope('foo', 'bar'), Scope('baz', 'bat')]
            )
        )
        self.assertTrue(self.oa2client.check_requested_scopes(['foo:bar']))
        self.assertTrue(self.oa2client.check_requested_scopes(['baz:bat']))
        self.assertFalse(self.oa2client.check_requested_scopes(['all:delete']))
        self.assertFalse(
            self.oa2client.check_requested_scopes(['all:delete', 'baz:bat'])
        )

    def test_check_response_type(self):
        """:meth:`.check_response_type` evaluates proposed response type."""
        self.assertTrue(self.oa2client.check_response_type('code'))
        self.assertFalse(self.oa2client.check_response_type('token'))

    def test_check_token_endpoint_auth_method(self):
        """:meth:`.check_token_endpoint_auth_method` allows post only."""
        self.assertTrue(
            self.oa2client.check_token_endpoint_auth_method(
                'client_secret_post'
            )
        )
        self.assertFalse(
            self.oa2client.check_token_endpoint_auth_method(
                'client_secret_basic'
            )
        )
        self.assertFalse(
            self.oa2client.check_token_endpoint_auth_method(
                'none'
            )
        )

    def test_get_default_redirect_uri(self):
        """:meth:`.get_default_redirect_uri` returns client redirect URI."""
        self.assertEqual(self.client.redirect_uri,
                         self.oa2client.get_default_redirect_uri())

    def test_has_client_secret(self):
        """:meth:`.has_client_secret` evaluates presence of client secret."""
        self.assertTrue(self.oa2client.has_client_secret())


class TestGetClient(TestCase):
    """Tests for :func:`oauth2.get_client`."""

    def setUp(self):
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
                grant_type='implicit',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            ),
            ClientGrantType(
                grant_type='password',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            )
        ]

    @mock.patch(f'{oauth2.__name__}.request')
    @mock.patch(f'{oauth2.__name__}.datastore')
    def test_get_client(self, mock_datastore, mock_request):
        """:func:`.get_client` returns an :class:`OAuth2Client`."""
        mock_request.auth = Session(
            session_id='1234-abcd',
            start_time=datetime.now(),
            user=User(
                username='foouser',
                email='foo@bar.com',
                user_id='12345'
            ),
            authorizations=Authorizations(
                scopes=[Scope('foo', 'bar'), Scope('baz', 'bat')]
            )
        )
        mock_datastore.load_client.return_value = (
            self.client, self.cred, self.auths, self.grant_types
        )
        oa2client = oauth2.get_client('252')

        self.assertEqual(sorted(oa2client.scopes),
                         sorted(['foo:bar', 'baz:bat']))
        self.assertTrue(oa2client.check_client_secret(self.secret))
        self.assertFalse(oa2client.check_client_secret('nope'))
        self.assertTrue(oa2client.check_grant_type('implicit'))
        self.assertTrue(oa2client.check_grant_type('password'))
        self.assertFalse(oa2client.check_grant_type('client_credentials'))
        self.assertTrue(
            oa2client.check_redirect_uri('https://foo.com/bar')
        )
        self.assertFalse(
            oa2client.check_redirect_uri('https://fdsa.com/nope')
        )
        self.assertTrue(oa2client.check_requested_scopes(['foo:bar']))
        self.assertTrue(oa2client.check_requested_scopes(['baz:bat']))
        self.assertFalse(oa2client.check_requested_scopes(['all:delete']))
        self.assertFalse(
            oa2client.check_requested_scopes(['all:delete', 'baz:bat'])
        )
        self.assertTrue(oa2client.check_response_type('code'))
        self.assertFalse(oa2client.check_response_type('token'))
        self.assertTrue(
            oa2client.check_token_endpoint_auth_method(
                'client_secret_post'
            )
        )
        self.assertFalse(
            oa2client.check_token_endpoint_auth_method(
                'client_secret_basic'
            )
        )
        self.assertFalse(
            oa2client.check_token_endpoint_auth_method(
                'none'
            )
        )
        self.assertEqual(self.client.redirect_uri,
                         oa2client.get_default_redirect_uri())
        self.assertTrue(oa2client.has_client_secret())

    @mock.patch(f'{oauth2.__name__}.datastore')
    def test_get_nonexistant_client(self, mock_datastore):
        """:func:`.get_client` returns None if client does not exist."""
        mock_datastore.NoSuchClient = datastore.NoSuchClient
        mock_datastore.load_client.side_effect = datastore.NoSuchClient

        self.assertIsNone(oauth2.get_client('252'))


class TestSaveToken(TestCase):
    """Tests for :func:`oauth2.save_token`."""

    @mock.patch(f'{oauth2.__name__}.request')
    @mock.patch(f'{oauth2.__name__}.SessionStore')
    def test_save_token(self, mock_SessionStore, mock_request):
        """Use the session store to persist a token as a session."""
        oa2request = mock.MagicMock(
            client=mock.MagicMock(scopes=[Scope('foo', 'bar')]),
            user=None,
        )
        mock_request.remote_addr = '127.0.0.1'
        oauth2.save_token({'access_token': 'footoken'}, oa2request)

        self.assertEqual(
            mock_SessionStore.current_session.return_value.create.call_count,
            1
        )
        (auths, ip, radr), kwargs \
            = mock_SessionStore.current_session.return_value.create.call_args
        self.assertEqual(auths.scopes, [Scope('foo', 'bar')])
        self.assertEqual(ip, '127.0.0.1')
        self.assertEqual(radr, '127.0.0.1')
        self.assertIsNone(kwargs['user'])
        self.assertIsNotNone(kwargs['client'])
        self.assertIsNotNone(kwargs['session_id'])


class TestCreateServer(TestCase):
    """Tests for :func:`oauth2.create_server`."""

    def test_create_server(self):
        """Instantiate an :class:`oauth2.AuthorizationServer`."""
        server = oauth2.create_server()
        self.assertIsInstance(server, oauth2.AuthorizationServer)


class TestInitApp(TestCase):
    """Tests for :func:`oauth2.init_app`."""

    @mock.patch(f'{oauth2.__name__}.AuthorizationServer')
    def test_init_app(self, mock_server_class):
        """Attach an :class:`oauth2.AuthorizationServer` to an app."""
        mock_server = mock.MagicMock()
        mock_server_class.return_value = mock_server
        app = mock.MagicMock()
        oauth2.init_app(app)
        self.assertEqual(app.server, mock_server)
        self.assertTrue(mock_server.init_app.called_with(app))
