"""Tests for :mod:`arxiv.users.auth.decorators`."""

import os
from unittest import TestCase, mock
from datetime import datetime
from pytz import timezone, UTC
import json

from flask import Flask, Blueprint
from flask import request, current_app
from werkzeug.exceptions import Unauthorized, Forbidden

from arxiv.base.middleware import wrap
from arxiv import status
from .. import tokens, scopes, decorators
from ... import domain

EASTERN = timezone('US/Eastern')


class TestScoped(TestCase):
    """Tests for :func:`.decorators.scoped`."""

    @mock.patch(f'{decorators.__name__}.request')
    def test_no_session(self, mock_request):
        """No session is present on the request."""
        mock_request.auth = None

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        with self.assertRaises(Unauthorized):
            protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_legacy_is_valid(self, mock_request):
        """A valid legacy session is available."""
        mock_request.auth = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
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
        mock_request.auth = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
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
    def test_scope_is_present(self, mock_request):
        """Session has required scope."""
        mock_request.auth = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
            user=domain.User(
                user_id='235678',
                email='foo@foo.com',
                username='foouser'
            ),
            authorizations=domain.Authorizations(
                scopes=[scopes.VIEW_SUBMISSION, scopes.CREATE_SUBMISSION]
            )
        )

        @decorators.scoped(scopes.CREATE_SUBMISSION)
        def protected():
            """A protected function."""

        # with self.assertRaises(Forbidden):
        protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_user_and_client_are_missing(self, mock_request):
        """Session does not user nor client information."""
        mock_request.auth = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
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
        mock_request.auth = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
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
        mock_request.auth = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
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

    @mock.patch(f'{decorators.__name__}.request')
    def test_session_has_global(self, mock_request):
        """Session has global scope, and authorizer func returns false."""
        mock_request.auth = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
            user=domain.User(
                user_id='235678',
                email='foo@foo.com',
                username='foouser'
            ),
            authorizations=domain.Authorizations(
                scopes=[scopes.CREATE_SUBMISSION.as_global()]
            )
        )

        def return_false(session: domain.Session) -> bool:
            return False

        @decorators.scoped(scopes.CREATE_SUBMISSION, authorizer=return_false)
        def protected():
            """A protected function."""

        protected()

    @mock.patch(f'{decorators.__name__}.request')
    def test_session_has_resource_scope(self, mock_request):
        """Session has resource scope, and authorizer func returns false."""
        mock_request.auth = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
            user=domain.User(
                user_id='235678',
                email='foo@foo.com',
                username='foouser'
            ),
            authorizations=domain.Authorizations(
                scopes=[scopes.EDIT_SUBMISSION.for_resource('1')]
            )
        )

        def return_false(session: domain.Session) -> bool:
            return False

        def get_resource(*args, **kwargs) -> bool:
            return '1'

        @decorators.scoped(scopes.EDIT_SUBMISSION, resource=get_resource,
                           authorizer=return_false)
        def protected():
            """A protected function."""

        protected()
