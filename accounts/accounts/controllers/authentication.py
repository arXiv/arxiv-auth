"""
Controllers for arXiv accounts application.

When a user logs in via the accounts service, they are issued a session key
that is stored as a cookie in their browser. That session ID is registered in
the distributed keystore, along with claims about the user's identity and
privileges in the system (based on their role). In subsequent requests handled
by the UI ingress, the authenticator service uses that session key to validate
the authenticated session, and to retrieve corresponding identity and
authorization information.
"""

from typing import Dict, Tuple, Any, Optional
import re

from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import InternalServerError
from flask import Markup

from wtforms import StringField, PasswordField, Form
from wtforms.validators import DataRequired

from retry import retry

from arxiv import status
from arxiv.base import logging

from arxiv_auth.domain import User, Authorizations, Session

from arxiv_auth.auth.sessions import SessionStore

from arxiv_auth.legacy import exceptions, sessions as legacy_sessions
from arxiv_auth.legacy.authenticate import authenticate
from arxiv_auth.legacy.util import transaction

from accounts import config

logger = logging.getLogger(__name__)

ResponseData = Tuple[dict, int, dict]


def login(method: str, form_data: MultiDict, ip: str,
          next_page: str, track: str = '') -> ResponseData:
    """
    Provide the login form.

    Parameters
    ----------
    form_data : MultiDict
        Should include `username` and `password` data.
    ip : str
        IP or hostname of client.
    next_page : str
        Page to which the user should be redirected upon login.

    Returns
    -------
    dict
        Additional data to add to the response.
    int
        Status code. This should be 303 (See Other) if all goes well.
    dict
        Headers to add to the response.

    """
    sessions = SessionStore.current_session()
    if method == 'GET':
        logger.debug('Request for login form')
        # TODO: If a permanent token is provided, attempt to log the user in,
        # and redirect if successful. Otherwise, proceed as normal without
        # complaint.
        if not next_page or good_next_page(next_page):
            response_data = {'form': LoginForm(), 'next_page': next_page}
            return response_data, status.HTTP_200_OK, {}
        else:
            response_data = {'form': LoginForm(), 'error':'next_page is invalid'}
            return response_data, status.HTTP_400_BAD_REQUEST, {}

    logger.debug('Login form submitted')
    form = LoginForm(form_data)
    data: Dict[str, Any] = {'form': form, 'next_page': next_page}
    if not form.validate():
        logger.debug('Form data is not valid')
        return data, status.HTTP_400_BAD_REQUEST, {}

    logger.debug('Login form is valid')

    try:    # Attempt to authenticate the user with the credentials provided.
        user, auths = _do_authn(form.username.data, form.password.data)
    except exceptions.AuthenticationFailed as ex:
        logger.debug('Authentication failed for %s: %s', form.username.data, ex)
        data.update({'error': 'Invalid username or password.'})
        return data, status.HTTP_400_BAD_REQUEST, {}
    except Exception as ex:
        logger.exception('Error during Authentication for %s', form.username.data)
        # To the perspective of the attacker, same as AuthenticationFailed:
        data.update({'error': 'Invalid username or password.'})
        return data, status.HTTP_400_BAD_REQUEST, {}

    if not user.verified:
        data.update({
            'error': Markup(
                'Your account has not yet been verified. Please contact '
                '<a href="mailto:help@arxiv.org">help@arxiv.org</a> if '
                'you believe this to be in error.'
            )
        })
        return data, status.HTTP_400_BAD_REQUEST, {}

    try:    # Create a session in the distributed session store.
        session = sessions.create(auths, ip, ip, track, user=user)
        cookie = sessions.generate_cookie(session)
        logger.debug('Created session: %s', session.session_id)
    except sessions.exceptions.SessionCreationFailed as e:
        logger.debug('Could not create session: %s', e)
        logger.info('Could not create session: %s', e)
        raise InternalServerError('Cannot log in') from e  # type: ignore

    try:    # Create a session in the legacy session store.
        c_session, c_cookie = _do_login(auths, ip, track, user)
    except exceptions.SessionCreationFailed as e:
        logger.debug('Could not create legacy session: %s', e)
        logger.info('Could not create legacy session: %s', e)
        raise InternalServerError('Cannot log in') from e  # type: ignore

    # The UI route should use these to set cookies on the response.
    data.update({
        'cookies': {
            'auth_session_cookie': (cookie, session.expires),
            'classic_cookie': (c_cookie, c_session.expires)
        }
    })
    next_page = next_page if good_next_page(next_page) else config.DEFAULT_LOGIN_REDIRECT_URL
    return data, status.HTTP_303_SEE_OTHER, {'Location': next_page}


def logout(session_cookie: Optional[str],
           classic_session_cookie: Optional[str],
           next_page: str) -> ResponseData:
    """
    Log the user out, and redirect to arXiv.org.

    Parameters
    ----------
    session_id : str or None
        If not None, invalidates the session.
    classic_session_id : str or None
        If not None, invalidates the session.
    next_page : str
        Page to which the user should be redirected upon logout.

    Returns
    -------
    dict
        Additional data to add to the response.
    int
        Status code. This should be 303 (See Other).
    dict
        Headers to add to the response.

    """
    logger.debug('Request to log out')
    sessions = SessionStore.current_session()
    if session_cookie:
        try:
            sessions.delete(session_cookie)
        except sessions.exceptions.SessionDeletionFailed as e:
            logger.debug('Logout failed: %s', e)

    if classic_session_cookie:
        try:
            with transaction():
                _do_logout(classic_session_cookie)
        except exceptions.SessionDeletionFailed as e:
            logger.debug('Logout failed: %s', e)
        except exceptions.UnknownSession as e:
            logger.debug('Unknown session: %s', e)

    data = {
        'cookies': {
            'auth_session_cookie': ('', 0),
            'classic_cookie': ('', 0)
        }
    }
    return data, status.HTTP_303_SEE_OTHER, {'Location': next_page}


class LoginForm(Form):
    """Log in form."""

    username = StringField('Username or e-mail', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


# These are broken out to add retry and transaction logic.
@retry(exceptions.Unavailable, tries=3, delay=0.5, backoff=2)
def _do_authn(username: str, password: str) -> Tuple[User, Authorizations]:
    with transaction():
        return authenticate(username_or_email=username,
                            password=password)


@retry(exceptions.Unavailable, tries=3, delay=0.5, backoff=2)
def _do_login(auths: Authorizations, ip: str, tracking_cookie: str,
              user: User = None) -> Tuple[Session, str]:
    with transaction():
        c_session = legacy_sessions.create(auths, ip, ip, tracking_cookie, user=user)
        c_cookie = legacy_sessions.generate_cookie(c_session)
        logger.debug('Created classic session: %s', c_session.session_id)
        return c_session, c_cookie


@retry(exceptions.Unavailable, tries=3, delay=0.5, backoff=2)
def _do_logout(classic_session_cookie: str) -> None:
    with transaction():
        legacy_sessions.invalidate(classic_session_cookie)


def good_next_page(next_page: str) -> bool:
    """True if next_page is a valid query parameter for use with the login page."""
    return next_page == config.DEFAULT_LOGIN_REDIRECT_URL \
        or re.search(config.login_redirect_pattern, next_page)
