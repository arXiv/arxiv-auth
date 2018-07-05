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

    @mock.patch(f'{decorators.__name__}.request')
    def test_no_session(self, mock_request):
        """No session is present on the request."""
        mock_request.session = None

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        with self.assertRaises(Unauthorized):
            protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_legacy_is_valid(self, mock_request):
        """A valid legacy session is available."""
        mock_request.session = domain.Session(
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
    def test_scope_is_missing(self, mock_request):
        """Session does not have required scope."""
        mock_request.session = domain.Session(
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
    def test_user_and_client_are_missing(self, mock_request):
        """Session does not user nor client information."""
        mock_request.session = domain.Session(
            session_id='fooid',
            start_time=datetime.now(),
            authorizations=domain.Authorizations(
                scopes=[scopes.CREATE_SUBMISSION]
            )
        )

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        with self.assertRaises(Unauthorized):
            protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_authorizer_returns_false(self, mock_request):
        """Session has required scope, but authorizer func returns false."""
        mock_request.session = domain.Session(
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
        mock_request.session = domain.Session(
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

        def return_true(session: domain.Session) -> bool:
            return True

        @decorators.scoped(scopes.CREATE_SUBMISSION, authorizer=return_true)
        def protected():
            """A protected function."""

        protected()
