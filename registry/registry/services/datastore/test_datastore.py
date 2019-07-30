"""Tests for :mod:`registry.services.datastore`."""

from unittest import TestCase, mock
import os
from datetime import datetime, timedelta
from flask import Flask

from ...domain import Client, ClientCredential, ClientAuthorization, \
    ClientGrantType
from .. import datastore


MOCK_G = mock.MagicMock(
    __contains__=lambda g, key: not isinstance(getattr(g, key), mock.MagicMock)
)


def get_g():
    return MOCK_G


class TestRoundTrip(TestCase):
    """Round-trip tests for saving and loading client data."""

    def setUp(self):
        """Set up a temporary DB."""
        self.app = Flask('test')
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        datastore.init_app(self.app)
        with self.app.app_context():
            datastore.drop_all()
            datastore.create_all()

    def tearDown(self):
        """Tear down temporary DB."""
        with self.app.app_context():
            datastore.drop_all()

    @mock.patch(f'{datastore.__name__}.util.get_application_global', get_g)
    def test_save_load_new_client(self):
        """Save and load a new :class:`Client`."""
        # mock_get_g.return_value = MOCK_G
        client = Client(
            owner_id='252',
            name='fooclient',
            url='http://asdf.com',
            description='a client',
            redirect_uri='https://foo.com/bar'
        )
        with self.app.app_context():
            client_id = datastore.save_client(client)
            loaded_client, *_ = datastore.load_client(client_id)

        self.assertEqual(client.name, loaded_client.name)
        self.assertEqual(client.url, loaded_client.url)
        self.assertEqual(client.description, loaded_client.description)
        self.assertEqual(client.owner_id, loaded_client.owner_id)
        self.assertEqual(client.redirect_uri, loaded_client.redirect_uri)

    @mock.patch(f'{datastore.__name__}.util.get_application_global', get_g)
    def test_save_load_client(self):
        """Save and load an existing client with updated attributes."""
        with self.app.app_context():
            client_id = datastore.save_client(Client(
                owner_id='252',
                name='fooclient',
                url='http://asdf.com',
                description='a client',
                redirect_uri='https://foo.com/bar'
            ))
            original_client, *_ = datastore.load_client(client_id)
            client = Client(
                client_id=client_id,
                name='something else',
                owner_id='254',
                url='http://entirely.different',
                description='the same client, but better',
                redirect_uri='https://foo.com/baz'
            )
            datastore.save_client(client)
            loaded_client, *_ = datastore.load_client(client_id)

        self.assertEqual(client.name, loaded_client.name)
        self.assertEqual(client.url, loaded_client.url)
        self.assertEqual(client.description, loaded_client.description)
        self.assertEqual(client.owner_id, loaded_client.owner_id)
        self.assertEqual(client.redirect_uri, loaded_client.redirect_uri)

    @mock.patch(f'{datastore.__name__}.util.get_application_global', get_g)
    def test_save_load_new_client_with_credential(self):
        """Save and load a new client with a :class:`ClientCredential`."""
        client = Client(
            owner_id='252',
            name='fooclient',
            url='http://asdf.com',
            description='a client',
            redirect_uri='https://foo.com/bar'
        )
        cred = ClientCredential(client_secret='foohashedsecret')

        with self.app.app_context():
            client_id = datastore.save_client(client, cred)
            loaded_client, loaded_cred, *_ = datastore.load_client(client_id)

        self.assertEqual(client.name, loaded_client.name)
        self.assertEqual(client.url, loaded_client.url)
        self.assertEqual(client.description, loaded_client.description)
        self.assertEqual(client.owner_id, loaded_client.owner_id)
        self.assertEqual(client.redirect_uri, loaded_client.redirect_uri)
        self.assertEqual(cred.client_secret, loaded_cred.client_secret)

    @mock.patch(f'{datastore.__name__}.util.get_application_global', get_g)
    def test_save_load_new_client_with_auths_and_grants(self):
        """Save and load a new client with auths and grant types."""
        client = Client(
            owner_id='252',
            name='fooclient',
            url='http://asdf.com',
            description='a client',
            redirect_uri='https://foo.com/bar'
        )
        cred = ClientCredential(client_secret='foohashedsecret')
        auths = [ClientAuthorization(
            scope='foo:bar',
            requested=datetime.now() - timedelta(seconds=30),
            authorized=datetime.now()
        )]
        gtypes = [ClientGrantType(
            grant_type='implicit',
            requested=datetime.now() - timedelta(seconds=30),
            authorized=datetime.now()
        )]

        with self.app.app_context():
            client_id = datastore.save_client(client, cred, auths=auths,
                                              grant_types=gtypes)

            l_client, l_cred, l_auths, l_gtypes \
                = datastore.load_client(client_id)

        self.assertEqual(client.name, l_client.name)
        self.assertEqual(client.url, l_client.url)
        self.assertEqual(client.description, l_client.description)
        self.assertEqual(client.owner_id, l_client.owner_id)
        self.assertEqual(client.redirect_uri, l_client.redirect_uri)
        self.assertEqual(cred.client_secret, l_cred.client_secret)
        self.assertEqual(len(auths), len(l_auths))
        self.assertEqual(auths[0].scope, l_auths[0].scope)
        self.assertEqual(auths[0].requested, l_auths[0].requested)
        self.assertEqual(auths[0].authorized, l_auths[0].authorized)

        self.assertEqual(len(gtypes), len(l_gtypes))
        self.assertEqual(gtypes[0].grant_type, l_gtypes[0].grant_type)
        self.assertEqual(gtypes[0].requested, l_gtypes[0].requested)
        self.assertEqual(gtypes[0].authorized, l_gtypes[0].authorized)

    @mock.patch(f'{datastore.__name__}.util.get_application_global', get_g)
    def test_save_load_client_with_auths_and_grants(self):
        """Save and load an existing client with updated attributes."""
        with self.app.app_context():
            client_id = datastore.save_client(
                Client(
                    owner_id='252',
                    name='fooclient',
                    url='http://asdf.com',
                    description='a client',
                    redirect_uri='https://foo.com/bar'
                ),
                ClientCredential(client_secret='foohashedsecret'),
                auths=[
                    ClientAuthorization(
                        scope='foo:bar',
                        requested=datetime.now() - timedelta(seconds=30),
                        authorized=datetime.now()
                    ),
                    ClientAuthorization(
                        scope='totally:unrelated',
                        requested=datetime.now() - timedelta(seconds=30),
                        authorized=datetime.now()
                    )
                ],
                grant_types=[
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
                ])

            o_client, o_cred, o_auths, o_gtypes \
                = datastore.load_client(client_id)

        client = Client(
            client_id=client_id,
            name='something else',
            owner_id='254',
            url='http://entirely.different',
            description='the same client, but better',
            redirect_uri='https://foo.com/baz'
        )
        auths = [
            # Modify an existing scope auth.
            ClientAuthorization(
                authorization_id=o_auths[0].authorization_id,
                scope='baz:baz',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            ),
            # Create a new scope auth.
            ClientAuthorization(
                scope='baz:bat',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            )
            # Note that we left out a scope auth from the original set.
        ]
        gtypes = [
            # Modify an existing grant type auth.
            ClientGrantType(
                grant_type_id=o_gtypes[0].grant_type_id,
                grant_type='implicit',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            ),
            # Create a new grant type auth.
            ClientGrantType(
                grant_type='client_credentials',
                requested=datetime.now() - timedelta(seconds=30),
                authorized=datetime.now()
            )
            # Note that we left out a grant type auth from the original set.
        ]

        cred = ClientCredential(client_secret='notthesamesecret')
        with self.app.app_context():
            datastore.save_client(client, cred, auths=auths,
                                  grant_types=gtypes)

            l_client, l_cred, l_auths, l_gtypes \
                = datastore.load_client(client_id)

        # Put in same order as defined above.
        l_auths = sorted(l_auths, key=lambda o: o.authorization_id)
        l_gtypes = sorted(l_gtypes, key=lambda o: o.grant_type_id)

        self.assertEqual(client.name, l_client.name)
        self.assertEqual(client.url, l_client.url)
        self.assertEqual(client.description, l_client.description)
        self.assertEqual(client.owner_id, l_client.owner_id)
        self.assertEqual(client.redirect_uri, l_client.redirect_uri)
        self.assertEqual(len(auths), len(l_auths))
        for auth, l_auth in zip(auths, l_auths):
            self.assertEqual(auth.scope, l_auth.scope)
            self.assertEqual(auth.requested, l_auth.requested)
            self.assertEqual(auth.authorized, l_auth.authorized)

        self.assertEqual(len(gtypes), len(l_gtypes))
        for gtype, l_gtype in zip(gtypes, l_gtypes):
            self.assertEqual(gtype.grant_type, l_gtype.grant_type)
            self.assertEqual(gtype.requested, l_gtype.requested)
            self.assertEqual(gtype.authorized, l_gtype.authorized)
