"""Tests for :mod:`arxiv.users.auth.decorators`."""

import os
from unittest import TestCase, mock
from datetime import datetime
import json

from flask import Flask, Blueprint
from flask import request, current_app
from werkzeug.exceptions import Unauthorized, Forbidden

from arxiv.base.middleware import wrap
from arxiv import status
from .. import tokens, scopes, decorators
from ... import domain


class TestScoped(TestCase):
    """Tests for :func:`.decorators.scoped`."""

    @mock.patch(f'{decorators.__name__}.legacy')
    @mock.patch(f'{decorators.__name__}.request')
    def test_no_session(self, mock_request, mock_legacy):
        """No session is present on the request."""
        mock_request.environ = {'session': None}
        mock_legacy.is_configured.return_value = False

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        with self.assertRaises(Unauthorized):
            protected()

    @mock.patch(f'{decorators.__name__}.legacy')
    @mock.patch(f'{decorators.__name__}.current_app')
    @mock.patch(f'{decorators.__name__}.request')
    def test_no_session_legacy_available(self, mock_request, mock_app,
                                         mock_legacy):
        """No session is present on the request, but database is present."""
        mock_request.environ = {'session': None}
        mock_request.cookies = {'foo_cookie': 'sessioncookie123'}
        mock_app.config = {'CLASSIC_COOKIE_NAME': 'foo_cookie'}
        mock_legacy.is_configured.return_value = True
        mock_legacy.sessions.load.return_value = None

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        with self.assertRaises(Unauthorized):
            protected()

        self.assertEqual(mock_legacy.sessions.load.call_count, 1,
                         "An attempt is made to load a legacy session")

    @mock.patch(f'{decorators.__name__}.legacy')
    @mock.patch(f'{decorators.__name__}.current_app')
    @mock.patch(f'{decorators.__name__}.request')
    def test_legacy_is_valid(self, mock_request, mock_app, mock_legacy):
        """A valid legacy session is available."""
        mock_request.environ = {'session': None}
        mock_request.cookies = {'foo_cookie': 'sessioncookie123'}
        mock_app.config = {'CLASSIC_COOKIE_NAME': 'foo_cookie'}
        mock_legacy.is_configured.return_value = True
        mock_legacy.sessions.return_value = domain.Session(
            session_id='fooid',
            start_time=datetime.now(),
            user=domain.User(
                user_id='235678',
                email='foo@foo.com',
                username='foouser'
            ),
            authorizations=domain.Authorizations(
                scopes=[scopes.VIEW_SUBMISSION]
            )
        )

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        with self.assertRaises(Forbidden):
            protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_middleware_exception(self, mock_request):
        """Middleware has passed an exception."""
        mock_request.environ = {'session': RuntimeError('Nope!')}

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        with self.assertRaises(RuntimeError):
            protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_scope_is_missing(self, mock_request):
        """Session does not have required scope."""
        mock_request.environ = {
            'session': domain.Session(
                session_id='fooid',
                start_time=datetime.now(),
                user=domain.User(
                    user_id='235678',
                    email='foo@foo.com',
                    username='foouser'
                ),
                authorizations=domain.Authorizations(
                    scopes=[scopes.VIEW_SUBMISSION]
                )
            )
        }

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        with self.assertRaises(Forbidden):
            protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_user_and_client_are_missing(self, mock_request):
        """Session does not user nor client information."""
        mock_request.environ = {
            'session': domain.Session(
                session_id='fooid',
                start_time=datetime.now(),
                authorizations=domain.Authorizations(
                    scopes=[scopes.CREATE_SUBMISSION]
                )
            )
        }

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        with self.assertRaises(Unauthorized):
            protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_authorizer_returns_false(self, mock_request):
        """Session has required scope, but authorizer func returns false."""
        mock_request.environ = {
            'session': domain.Session(
                session_id='fooid',
                start_time=datetime.now(),
                user=domain.User(
                    user_id='235678',
                    email='foo@foo.com',
                    username='foouser'
                ),
                authorizations=domain.Authorizations(
                    scopes=[scopes.CREATE_SUBMISSION]
                )
            )
        }

        def return_false(session: domain.Session) -> bool:
            return False

        @decorators.scoped(scopes.CREATE_SUBMISSION, authorizer=return_false)
        def protected():
            """A protected function."""

        with self.assertRaises(Forbidden):
            protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_authorizer_returns_true(self, mock_request):
        """Session has required scope, and authorizer func returns true."""
        mock_request.environ = {
            'session': domain.Session(
                session_id='fooid',
                start_time=datetime.now(),
                user=domain.User(
                    user_id='235678',
                    email='foo@foo.com',
                    username='foouser'
                ),
                authorizations=domain.Authorizations(
                    scopes=[scopes.CREATE_SUBMISSION]
                )
            )
        }

        def return_true(session: domain.Session) -> bool:
            return True

        @decorators.scoped(scopes.CREATE_SUBMISSION, authorizer=return_true)
        def protected():
            """A protected function."""

        protected()
