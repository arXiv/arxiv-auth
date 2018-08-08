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
import uuid

from werkzeug import MultiDict, ImmutableMultiDict
from werkzeug.exceptions import BadRequest, InternalServerError
from flask import url_for

from wtforms import StringField, PasswordField, SelectField, \
    SelectMultipleField, BooleanField, Form, HiddenField
from wtforms.validators import DataRequired, Email, Length, URL, optional
from wtforms.widgets import ListWidget, CheckboxInput, Select

import pycountry

from arxiv import status
from arxiv.base import logging
from accounts.services import legacy, sessions, users

from .util import MultiCheckboxField, OptGroupSelectField


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
    if method == 'GET':
        logger.debug('Request for login form')
        # TODO: If a permanent token is provided, attempt to log the user in,
        # and redirect if successful. Otherwise, proceed as normal without
        # complaint.
        response_data = {'form': LoginForm(), 'next_page': next_page}
        return response_data, status.HTTP_200_OK, {}

    logger.debug('Login form submitted')
    form = LoginForm(form_data)
    data: Dict[str, Any] = {'form': form}
    if not form.validate():
        logger.debug('Form data is not valid')
        return data, status.HTTP_400_BAD_REQUEST, {}

    logger.debug('Login form is valid')
    # Attempt to authenticate the user with the credentials provided.
    try:
        userdata, auths = users.authenticate(
            username_or_email=form.username.data,
            password=form.password.data
        )
    except users.exceptions.AuthenticationFailed as e:
        logger.debug('Authentication failed for %s with %s',
                     form.username.data, form.password.data)
        data.update({'error': 'Invalid username or password.'})
        return data, status.HTTP_400_BAD_REQUEST, {}

    # Create a session in the distributed session store.
    try:
        session, cookie = sessions.create(userdata, auths, ip, ip, track)
        logger.debug('Created session: %s', session.session_id)
    except sessions.exceptions.SessionCreationFailed as e:
        logger.debug('Could not create session: %s', e)
        raise InternalServerError('Cannot log in') from e  # type: ignore

    # Create a session in the legacy session store.
    try:
        c_session, c_cookie = legacy.create(userdata, auths, ip, ip, track)
        logger.debug('Created classic session: %s', c_session.session_id)
    except legacy.exceptions.SessionCreationFailed as e:
        logger.debug('Could not create legacy session: %s', e)
        raise InternalServerError('Cannot log in') from e  # type: ignore

    # The UI route should use these to set cookies on the response.
    data.update({
        'cookies': {
            'session_cookie': (cookie, session.expires),
            'classic_cookie': (c_cookie, c_session.expires)
        }
    })
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
    if session_cookie:
        try:
            sessions.delete(session_cookie)
        except sessions.exceptions.SessionDeletionFailed as e:
            logger.debug('Logout failed: %s', e)

    if classic_session_cookie:
        try:
            legacy.invalidate(classic_session_cookie)
        except legacy.exceptions.SessionDeletionFailed as e:
            logger.debug('Logout failed: %s', e)
        except legacy.exceptions.UnknownSession as e:
            logger.debug('Unknown session: %s', e)

    data = {
        'cookies': {
            'session_cookie': ('', 0),
            'classic_cookie': ('', 0)
        }
    }
    return data, status.HTTP_303_SEE_OTHER, {'Location': next_page}


class LoginForm(Form):
    """Log in form."""

    username = StringField('Username or e-mail', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
