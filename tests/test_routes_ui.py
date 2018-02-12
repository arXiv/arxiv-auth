"""Tests for :mod:`accounts.routes.external_ui`."""

from unittest import TestCase, mock
from datetime import datetime
import jwt
from flask import Flask
from accounts.factory import create_web_app

from typing import Any, Optional


def generate_token(app: Flask, claims: dict) -> str:
    """Helper function for generating a JWT."""
    secret = app.config.get('JWT_SECRET')
    return jwt.encode(claims, secret, algorithm='HS256') #type: ignore


class TestUIRoutes(TestCase):
    """Sample tests for UI routes."""

    def setUp(self) -> None:
        """Initialize the Flask application, and get a client for testing."""
        self.app = create_web_app()
        self.client = self.app.test_client()

    @mock.patch('accounts.controllers.baz.get_baz')
    def test_get_baz(self, mock_get_baz: Any) -> None:
        """Endpoint /accounts/ui/baz/<int> returns an HTML page about a Baz."""
        mock_get_baz.return_value = {'mukluk': 1, 'foo': 'bar'}, 200, {}

        response = self.client.get('/accounts/ui/baz/1')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'],
                         'text/html; charset=utf-8')

    @mock.patch('accounts.controllers.things.get_thing')
    def test_get_thing(self, mock_get_thing: Any) -> None:
        """Endpoint /accounts/ui/thing/<int> returns HTML page about a Thing."""
        foo_data = {'id': 4, 'name': 'First thing', 'created': datetime.now()}
        mock_get_thing.return_value = foo_data, 200, {}

        token = generate_token(self.app, {'scope': ['read:thing']})

        response = self.client.get('/accounts/ui/thing/4',
                                   headers={'Authorization': token})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'],
                         'text/html; charset=utf-8')
