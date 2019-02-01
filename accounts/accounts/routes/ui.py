"""Provides Flask integration for the external user interface."""

from typing import Any, Callable
from datetime import datetime, timedelta
from functools import wraps
from pytz import timezone, UTC
from flask import Blueprint, render_template, url_for, abort, request, \
    make_response, redirect, current_app, send_file, Response
from arxiv import status
from arxiv.users.auth.decorators import scoped
from arxiv.users.auth import scopes
from arxiv.users import domain
from arxiv.base import logging
from accounts.controllers import captcha_image, registration, authentication

from werkzeug.exceptions import BadRequest
from werkzeug.http import parse_cookie
from werkzeug import MultiDict

EASTERN = timezone('US/Eastern')

logger = logging.getLogger(__name__)

blueprint = Blueprint('ui', __name__, url_prefix='')


def user_is_owner(session: domain.Session, user_id: str, **kw: Any) -> bool:
    """Determine whether the authenticated user matches the requested user."""
    return bool(session.user.user_id == user_id)


def anonymous_only(func: Callable) -> Callable:
    """Redirect logged-in users to their profile."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if request.session:
            user = request.session.user
            target = url_for('account')
            content = redirect(target, code=status.HTTP_303_SEE_OTHER)
            response = make_response(content)
            return response
        return func(*args, **kwargs)
    return wrapper


def set_cookies(response: Response, data: dict) -> None:
    """
    Update a :class:`.Response` with cookies in controller data.

    Contollers seeking to update cookies must include a 'cookies' key
    in their response data.
    """
    # Set the session cookie.
    cookies = data.pop('cookies')
    if cookies is None:
        return None
    for cookie_key, (cookie_value, expires) in cookies.items():
        cookie_name = current_app.config[f'{cookie_key.upper()}_NAME']
        max_age = timedelta(seconds=expires)
        # expires_date = expires_date.replace(tzinfo=EASTERN)
        logger.debug('Set cookie %s with %s, max_age %s',
                     cookie_name, cookie_value, max_age)
        domain = current_app.config['AUTH_SESSION_COOKIE_DOMAIN']
        params = dict(httponly=True, domain=domain)
        if current_app.config['AUTH_SESSION_COOKIE_SECURE']:
            # Setting samesite to lax, to allow reasonable links to
            # authenticated views using GET requests.
            params.update({'secure': True, 'samesite': 'lax'})
        response.set_cookie(cookie_name, cookie_value, max_age=max_age,
                            **params)


# This is unlikely to be useful once the classic submission UI is disabled.
def unset_submission_cookie(response: Response) -> None:
    """
    Unset the legacy Catalyst submission cookie.

    In addition to the authenticated session (which was originally from the
    Tapir auth system), Catalyst also tracks a session used specifically for
    the submission process. The legacy Catalyst controller sets this
    automatically, so we don't need to do anything on login. But on logout,
    if this cookie is not cleared, Catalyst may attempt to use the same
    submission session upon subsequent logins. This can lead to weird
    inconsistencies.
    """
    response.set_cookie('submit_session', '', max_age=0, httponly=True)


def unset_permanent_cookie(response: Response) -> None:
    """
    Users who elect a permanent cookie expect it to be unset when they log out.

    If it is not unset, legacy components will attempt to log them back in.
    """
    permanent_cookie_name = current_app.config['CLASSIC_PERMANENT_COOKIE_NAME']
    response.set_cookie(permanent_cookie_name, '', max_age=0, expires=0,
                        httponly=True)


def detect_and_clobber_dupe_cookies(response: Response) -> None:
    raw_cookie = request.environ.get('HTTP_COOKIE', None)
    if raw_cookie is None:
        return None
    cookies = parse_cookie(raw_cookie, cls=MultiDict)
    classic_cookie_name = current_app.config['CLASSIC_COOKIE_NAME']
    permanent_cookie_name = current_app.config['CLASSIC_PERMANENT_COOKIE_NAME']
    domain = current_app.config['AUTH_SESSION_COOKIE_DOMAIN']
    print("!!", cookies)
    if len(cookies.getlist(classic_cookie_name)) > 1:
        response.set_cookie(classic_cookie_name, '', max_age=0, expires=0)
        response.set_cookie(classic_cookie_name, '', max_age=0, expires=0, domain=domain.lstrip('.'))
        response.set_cookie(classic_cookie_name, '', max_age=0, expires=0, domain=domain)
    if len(cookies.getlist(permanent_cookie_name)) > 1:
        response.set_cookie(permanent_cookie_name, '', max_age=0, expires=0)
        response.set_cookie(permanent_cookie_name, '', max_age=0, expires=0, domain=domain.lstrip('.'))
        response.set_cookie(permanent_cookie_name, '', max_age=0, expires=0, domain=domain)


# @blueprint.route('/register', methods=['GET', 'POST'])
@anonymous_only
def register() -> Response:
    """Interface for creating new accounts."""
    captcha_secret = current_app.config['CAPTCHA_SECRET']
    ip_address = request.remote_addr
    next_page = request.args.get('next_page', url_for('account'))
    data, code, headers = registration.register(request.method, request.form,
                                                captcha_secret, ip_address,
                                                next_page)

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code is status.HTTP_303_SEE_OTHER:
        response = make_response(redirect(headers['Location'], code=code))
        set_cookies(response, data)
        return response
    content = render_template("accounts/register.html", **data)
    response = make_response(content, code, headers)
    return response


# @blueprint.route('/<string:user_id>/profile', methods=['GET'])
# @scoped(scopes.VIEW_PROFILE, authorizer=user_is_owner)
# def view_profile(user_id: str) -> Response:
#     """User can view their account information."""
#     data, code, headers = registration.view_profile(user_id, request.session)
#     return render_template("accounts/profile.html", **data)


# @blueprint.route('/<string:user_id>/profile/edit', methods=['GET', 'POST'])
# @scoped(scopes.EDIT_PROFILE, authorizer=user_is_owner)
# def edit_profile(user_id: str) -> Response:
#     """User can update their account information."""
#     data, code, headers = registration.edit_profile(request.method, user_id,
#                                                     request.session,
#                                                     request.form,
#                                                     request.remote_addr)
#     if code is status.HTTP_303_SEE_OTHER:
#         target = url_for('ui.view_profile', user_id=user_id)
#         response = make_response(redirect(target, code=code))
#         set_cookies(response, data)
#         return response
#     content = render_template("accounts/edit_profile.html", **data)
#     response = make_response(content, code, headers)
#     return response


@blueprint.route('/login', methods=['GET', 'POST'])
@anonymous_only
def login() -> Response:
    """User can log in with username and password, or permanent token."""
    ip_address = request.remote_addr
    form_data = request.form
    next_page = request.args.get('next_page', url_for('account'))
    logger.debug('Request to log in, then redirect to %s', next_page)
    data, code, headers = authentication.login(request.method,
                                               form_data, ip_address,
                                               next_page)
    data.update({'pagetitle': 'Log in to arXiv'})
    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code is status.HTTP_303_SEE_OTHER:
        # Set the session cookie.
        response = make_response(redirect(headers.get('Location'), code=code))
        set_cookies(response, data)
        unset_submission_cookie(response)    # Fix for ARXIVNG-1149.
        return response

    # Form is invalid, or login failed.
    response = Response(
        render_template("accounts/login.html", **data),
        status=code
    )
    if request.method == 'GET':
        detect_and_clobber_dupe_cookies(response)
    return response


@blueprint.route('/logout', methods=['GET'])
def logout() -> Response:
    """Log out of arXiv."""
    session_cookie_key = current_app.config['AUTH_SESSION_COOKIE_NAME']
    classic_cookie_key = current_app.config['CLASSIC_COOKIE_NAME']
    session_cookie = request.cookies.get(session_cookie_key, None)
    classic_cookie = request.cookies.get(classic_cookie_key, None)
    next_page = request.args.get('next_page', url_for('ui.login'))
    logger.debug('Request to log out, then redirect to %s', next_page)
    data, code, headers = authentication.logout(session_cookie, classic_cookie,
                                                next_page)
    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code is status.HTTP_303_SEE_OTHER:
        logger.debug('Redirecting to %s: %i', headers.get('Location'), code)
        response = make_response(redirect(headers.get('Location'), code=code))
        set_cookies(response, data)
        unset_submission_cookie(response)    # Fix for ARXIVNG-1149.
        # Partial fix for ARXIVNG-1653, ARXIVNG-1644
        unset_permanent_cookie(response)
        return response
    return redirect(next_page, code=status.HTTP_302_FOUND)


# @blueprint.route('/captcha', methods=['GET'])
@anonymous_only
def captcha() -> Response:
    """Provide the image for stateless captcha."""
    secret = current_app.config['CAPTCHA_SECRET']
    font = current_app.config.get('CAPTCHA_FONT')
    token = request.args.get('token')
    data, code, headers = captcha_image.get(token, secret, request.remote_addr, font)
    return send_file(data['image'], mimetype=data['mimetype']), code, headers
