"""Tests for :class:`arxiv.users.auth.Auth`."""

from unittest import TestCase, mock
from datetime import datetime
from pytz import timezone, UTC
from ... import auth, domain

EASTERN = timezone('US/Eastern')


class TestAuthExtension(TestCase):
    """Tests for :class:`arxiv.users.auth.Auth`."""

    @mock.patch(f'{auth.__name__}.legacy')
    @mock.patch(f'{auth.__name__}.request')
    def test_no_session_legacy_available(self, mock_request, mock_legacy):
        """No session is present on the request, but database is present."""
        mock_request.environ = {'session': None}
        mock_request.cookies = {'foo_cookie': 'sessioncookie123'}
        mock_app = mock.MagicMock(
            config={'CLASSIC_COOKIE_NAME': 'foo_cookie'}
        )
        inst = auth.Auth(mock_app)

        mock_legacy.is_configured.return_value = True
        mock_legacy.sessions.load.return_value = None

        inst.load_session()
        self.assertIsNone(mock_request.session)

        self.assertEqual(mock_legacy.sessions.load.call_count, 1,
                         "An attempt is made to load a legacy session")

    @mock.patch(f'{auth.__name__}.legacy')
    @mock.patch(f'{auth.__name__}.request')
    def test_legacy_is_valid(self, mock_request, mock_legacy):
        """A valid legacy session is available."""
        mock_request.environ = {'session': None}
        mock_request.cookies = {'foo_cookie': 'sessioncookie123'}
        mock_app = mock.MagicMock(
            config={'CLASSIC_COOKIE_NAME': 'foo_cookie'}
        )
        mock_request.session = None
        mock_legacy.is_configured.return_value = True
        session = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
            user=domain.User(
                user_id='235678',
                email='foo@foo.com',
                username='foouser'
            ),
            authorizations=domain.Authorizations(
                scopes=[auth.scopes.VIEW_SUBMISSION]
            )
        )
        mock_legacy.sessions.load.return_value = session

        inst = auth.Auth(mock_app)
        # ARXIVNG-1920 using request.session is deprecated.
        with self.assertWarns(DeprecationWarning):
            inst.load_session()
        self.assertEqual(mock_request.session, session,
                         "Session is attached to the request")

    @mock.patch(f'{auth.__name__}.legacy')
    @mock.patch(f'{auth.__name__}.request')
    def test_auth_session_rename(self, mock_request, mock_legacy):
        """
        The auth session is accessed via ``request.auth``.

        Per ARXIVNG-1920 using ``request.session`` is deprecated.
        """
        mock_request.environ = {'session': None}
        mock_request.cookies = {'foo_cookie': 'sessioncookie123'}
        mock_app = mock.MagicMock(
            config={'CLASSIC_COOKIE_NAME': 'foo_cookie',
                    'AUTH_UPDATED_SESSION_REF': True}
        )
        mock_request.session = None
        mock_request.auth = None
        mock_legacy.is_configured.return_value = True
        session = domain.Session(
            session_id='fooid',
            start_time=datetime.now(tz=UTC),
            user=domain.User(
                user_id='235678',
                email='foo@foo.com',
                username='foouser'
            ),
            authorizations=domain.Authorizations(
                scopes=[auth.scopes.VIEW_SUBMISSION]
            )
        )
        mock_legacy.sessions.load.return_value = session

        inst = auth.Auth(mock_app)
        inst.load_session()
        self.assertEqual(mock_request.auth, session,
                         "Session is attached to the request")
        self.assertIsNone(mock_request.session, "request.session is not set")

    @mock.patch(f'{auth.__name__}.request')
    def test_middleware_exception(self, mock_request):
        """Middleware has passed an exception."""
        mock_request.environ = {'session': RuntimeError('Nope!')}
        mock_app = mock.MagicMock(
            config={'CLASSIC_COOKIE_NAME': 'foo_cookie'}
        )

        inst = auth.Auth(mock_app)
        with self.assertRaises(RuntimeError):
            inst.load_session()
