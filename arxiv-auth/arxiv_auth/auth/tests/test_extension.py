"""Tests for :class:`arxiv.users.auth.Auth`."""
from logging import DEBUG
from flask.globals import current_app
import pytest

from datetime import datetime
from pytz import timezone, UTC
from ... import auth, domain

EASTERN = timezone('US/Eastern')

@pytest.fixture
def app_with_cookie(app):
    app.config['CLASSIC_COOKIE_NAME'] = 'foo_cookie'
    return app

def test_no_session_legacy_available(mocker, app_with_cookie):
    """No session is present on the request, but database is present."""
    inst = app_with_cookie.config['arxiv_auth.Auth']
    auth.logger.setLevel(DEBUG)
    with app_with_cookie.test_request_context():
        mock_legacy = mocker.patch(f'{auth.__name__}.legacy')
        mock_request = mocker.patch(f'{auth.__name__}.request')
        mock_request.environ = {'session': None,
                                'HTTP_COOKIE': 'foo_cookie=sessioncookie123'}

        mock_legacy.is_configured.return_value = True
        mock_legacy.sessions.load.return_value = None

        inst.load_session()
        assert mock_request.session is None

        assert mock_legacy.sessions.load.call_count == 1, "An attempt is made to load a legacy session"

def test_legacy_is_valid(mocker, app_with_cookie):
    """A valid legacy session is available."""
    app_with_cookie.config['AUTH_UPDATED_SESSION_REF'] = True
    inst = app_with_cookie.config['arxiv_auth.Auth']
    with app_with_cookie.test_request_context():
        mock_legacy = mocker.patch(f'{auth.__name__}.legacy')
        mock_request = mocker.patch(f'{auth.__name__}.request')

        mock_request.environ = {'session': None,
                                'HTTP_COOKIE': 'foo_cookie=sessioncookie123'}

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

        inst.load_session()
        assert mock_request.auth == session, "Session is attached to the request at auth"

def test_auth_session_rename(mocker, app_with_cookie):
    """
    The auth session is accessed via ``request.auth``.

    Per ARXIVNG-1920 using ``request.auth`` is deprecated.
    """
    app_with_cookie.config['AUTH_UPDATED_SESSION_REF'] = True
    inst = app_with_cookie.config['arxiv_auth.Auth']
    with app_with_cookie.test_request_context():
        mock_legacy = mocker.patch(f'{auth.__name__}.legacy')
        mock_request = mocker.patch(f'{auth.__name__}.request')
        mock_request.environ = {'session': None,
                                'HTTP_COOKIE': 'foo_cookie=sessioncookie123'}
        mock_request.cookies = {'foo_cookie': 'sessioncookie123'}

        mock_request.auth = None
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

        inst.load_session()
        assert mock_request.auth == session, "Session is attached to the request"
        assert mock_request.session is None, "request.session is not set"


def test_middleware_exception(mocker, app_with_cookie):
    """Middleware has passed an exception."""
    inst = app_with_cookie.config['arxiv_auth.Auth']
    with app_with_cookie.test_request_context():
        mock_request  = mocker.patch(f'{auth.__name__}.request')
        mock_request.environ = {'session': RuntimeError('Nope!')}


        with pytest.raises(RuntimeError):
            inst.load_session()
