"""Tests for :mod:`accounts.routes.external_api`."""

from unittest import TestCase, mock
from datetime import datetime
import json
import jsonschema
from flask import Flask
from accounts.factory import create_web_app
import jwt

from typing import Any, Optional


def generate_token(app: Flask, claims: dict) -> str:
    """Helper function for generating a JWT."""
    secret = app.config.get('JWT_SECRET')
    return jwt.encode(claims, secret, algorithm='HS256') #type: ignore


class TestExternalAPIRoutes(TestCase):
    """Sample tests for external API routes."""

    def setUp(self) -> None:
        """Initialize the Flask application, and get a client for testing."""
        self.app = create_web_app()
        self.client = self.app.test_client()

    @mock.patch('accounts.controllers.baz.get_baz')
    def test_get_baz(self, mock_get_baz: Any) -> None:
        """Endpoint /accounts/api/baz/<int> returns JSON about a Baz."""
        with open('schema/baz.json') as f:
            schema = json.load(f)

        foo_data = {'mukluk': 1, 'foo': 'bar'}
        mock_get_baz.return_value = foo_data, 200, {}

        response = self.client.get('/accounts/api/baz/1')

        expected_data = {'mukluk': foo_data['mukluk'], 'foo': foo_data['foo']}

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(json.loads(response.data), expected_data)

        try:
            jsonschema.validate(json.loads(response.data), schema)
        except jsonschema.exceptions.SchemaError as e:
            self.fail(e)

    @mock.patch('accounts.controllers.things.get_thing')
    def test_get_thing(self, mock_get_thing: Any) -> None:
        """Endpoint /accounts/api/thing/<int> returns JSON about a Thing."""
        with open('schema/thing.json') as f:
            schema = json.load(f)

        foo_data = {'id': 4, 'name': 'First thing', 'created': datetime.now()}
        mock_get_thing.return_value = foo_data, 200, {}

        token = generate_token(self.app, {'scope': ['read:thing']})

        response = self.client.get('/accounts/api/thing/4',
                                   headers={'Authorization': token})

        expected_data = {
            'id': foo_data['id'], 'name': foo_data['name'],
            'created': foo_data['created'].isoformat() # type: ignore
        }

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(json.loads(response.data), expected_data)

        try:
            jsonschema.validate(json.loads(response.data), schema)
        except jsonschema.exceptions.SchemaError as e:
            self.fail(e)

    @mock.patch('accounts.controllers.things.create_a_thing')
    def test_create_thing(self, mock_create_a_thing: Any) -> None:
        """POST to endpoint /accounts/api/thing creates and stores a Thing."""
        foo_data = {'name': 'A New Thing'}
        return_data = {'name': 'A New Thing', 'id': 25,
                       'created': datetime.now(), 'url': '/accounts/api/thing/25'}
        headers = {'Location': '/accounts/api/thing/25'}
        mock_create_a_thing.return_value = return_data, 201, headers
        token = generate_token(self.app,
                               {'scope': ['read:thing', 'write:thing']})

        response = self.client.post('/accounts/api/thing',
                                    data=json.dumps(foo_data),
                                    headers={'Authorization': token},
                                    content_type='application/json')

        expected_data = {
            'id': return_data['id'], 'name': return_data['name'],
            'created': return_data['created'].isoformat(), #type: ignore
            'url': return_data['url']
        }

        self.assertEqual(response.status_code, 201, "Created")
        self.assertDictEqual(json.loads(response.data), expected_data)
