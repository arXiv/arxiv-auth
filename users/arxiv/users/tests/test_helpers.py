"""Tests for :mod:`.helpers`."""

from unittest import TestCase, mock
import os
from flask import Flask
from arxiv import status
from arxiv.base import Base
from arxiv.base.middleware import wrap
from .. import auth, helpers


class TestGenerateToken(TestCase):
    """Tests for :func:`.helpers.generate_token`."""

    @mock.patch(f'{helpers.__name__}.get_application_config')
    def test_token_is_usable(self, mock_get_config):
        """Verify that :func:`.helpers.generate_token` makes usable tokens."""
        mock_get_config.return_value = {'JWT_SECRET': 'thesecret'}
        os.environ['JWT_SECRET'] = 'thesecret'
        scope = [auth.scopes.VIEW_SUBMISSION, auth.scopes.EDIT_SUBMISSION,
                 auth.scopes.CREATE_SUBMISSION]
        token = helpers.generate_token("1234", "user@foo.com", "theuser",
                                       scope=scope)

        app = Flask('test')
        app.config['JWT_SECRET'] = 'thesecret'
        Base(app)
        auth.Auth(app)    # <- Install the Auth extension.
        wrap(app, [auth.middleware.AuthMiddleware])    # <- Install middleware.

        @app.route('/')
        @auth.decorators.scoped(auth.scopes.EDIT_SUBMISSION)
        def protected():
            return "this is protected"

        client = app.test_client()
        with app.app_context():
            response = client.get('/')
            self.assertEqual(response.status_code,
                             status.HTTP_401_UNAUTHORIZED)

            response = client.get('/', headers={'Authorization': token})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
