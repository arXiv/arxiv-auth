"""Controllers for arXiv accounts application."""

from typing import Dict, Tuple, Any, Optional
import uuid
from werkzeug import MultiDict, ImmutableMultiDict
from werkzeug.exceptions import BadRequest, InternalServerError

from arxiv import status
from arxiv.base import logging
from accounts.services import session_store as sessions
from accounts.services import classic_session_store as classic
from accounts.services import exceptions, user_data
from .forms import LoginForm, RegistrationForm#, ProfileForm

logger = logging.getLogger(__name__)

ResponseData = Tuple[dict, int, dict]


def generate_tracking_cookie(ip_address: str) -> bytes:
    return f'{ip_address}.{uuid.uuid4()}'.encode('utf-8')


def get_login() -> ResponseData:
    """
    Get the login form.

    Returns
    -------
    dict
        Additional data to add to the response.
    int
        Status code. This should be 200 (OK) if all goes well.
    dict
        Headers to add to the response.

    """
    logger.debug('Request for login form')
    return {'form': LoginForm()}, status.HTTP_200_OK, {}


def post_login(form_data: MultiDict, ip_address: str, next_page: str,
               tracking_cookie: str = '') -> ResponseData:
    """
    Process submitted login form and log the user in.

    Parameters
    ----------
    form_data : MultiDict
        Should include `username` and `password` data.
    ip_address : str
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
    logger.debug('Login form submitted')
    form = LoginForm(form_data)
    data: Dict[str, Any] = {}
    if form.validate():
        logger.debug('Login form is valid')
        try:
            userdata, auths = user_data.authenticate(
                username_or_email=form.username.data,
                password=form.password.data
            )
        except user_data.exceptions.AuthenticationFailed as e:
            raise BadRequest('Invalid username or password') from e
        try:
            session, cookie = sessions.create(userdata, auths, ip_address,
                                              ip_address, tracking_cookie)
            logger.debug('Created session: %s', session.session_id)
            classic_session, classic_cookie = classic.sessions.create(
                userdata,
                ip_address,
                ip_address,
                tracking_cookie
            )
            logger.debug('Created classic session: %s',
                         classic_session.session_id)
        except exceptions.SessionCreationFailed as e:
            logger.debug('Could not create session: %s', e)
            raise InternalServerError('Could not log in') from e

        data.update({'session_cookie': cookie,
                     'classic_cookie': classic_cookie})
        return data, status.HTTP_303_SEE_OTHER, {'Location': next_page}

    data.update({'form': form})
    return data, status.HTTP_200_OK, {}


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
            sessions.invalidate(session_cookie)
        except exceptions.SessionDeletionFailed as e:
            logger.debug('Logout failed: %s', e)
            raise InternalServerError('Could not log out') from e
    if classic_session_cookie:
        try:
            classic.sessions.invalidate(classic_session_cookie)
        except exceptions.SessionDeletionFailed as e:
            logger.debug('Logout failed: %s', e)
            raise InternalServerError('Could not log out') from e

    return {}, status.HTTP_303_SEE_OTHER, {'Location': next_page}


def get_register() -> ResponseData:
    form = RegistrationForm()
    return {'form': form}, status.HTTP_200_OK, {}


def post_register(form_data: MultiDict) -> ResponseData:
    """
    Processes submitted registration form, and create a new user.
    """
    logger.debug('Registration form submitted')
    form = RegistrationForm(form_data)
    if form.validate():
        logger.debug('Registration form is valid')
        print(form.to_domain())
    return {'form': form}, status.HTTP_200_OK, {}

#
# def get_edit() -> ResponseData:
#     form = ProfileForm()
#     return {'form': form}, status.HTTP_200_OK, {}
