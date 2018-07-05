"""Provides Flask integration for the external user interface."""

from typing import Any, Callable
from functools import wraps
from flask import Blueprint, render_template, url_for, abort, request, \
    make_response, redirect, current_app, send_file, Response
from arxiv import status
from arxiv.users.auth.decorators import scoped
from arxiv.users.auth import scopes
from arxiv.users import domain
from accounts.controllers import captcha_image, registration, authentication

from werkzeug.exceptions import BadRequest

blueprint = Blueprint('ui', __name__, url_prefix='/user')


def user_is_owner(session: domain.Session, user_id: str, **kw: Any) -> bool:
    """Determine whether the authenticated user matches the requested user."""
    return bool(session.user.user_id == user_id)


@blueprint.before_request
def get_next_page() -> None:
    """Get the next page; this is where we'll redirect the user on success."""
    request.next_page = request.args.get('next_page', '')


def anonymous_only(func: Callable) -> Callable:
    """Redirect logged-in users to their profile."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if request.session:
            user = request.session.user
            target = url_for('ui.view_profile', user_id=user.user_id)
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
        response.set_cookie(cookie_name, cookie_value, expires=expires)


@blueprint.route('/register', methods=['GET', 'POST'])
@anonymous_only
def register() -> Response:
    """Interface for creating new accounts."""
    captcha_secret = current_app.config['CAPTCHA_SECRET']
    ip_address = request.remote_addr
    data, code, headers = registration.register(request.method, request.form,
                                                captcha_secret, ip_address)

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code is status.HTTP_201_CREATED:
        target = url_for('ui.view_profile', user_id=data['user_id'])
        response = make_response(redirect(target, code=code))
        set_cookies(response, data)
        return response
    content = render_template("accounts/register.html", **data)
    response = make_response(content, code, headers)
    return response


@blueprint.route('/<string:user_id>/profile', methods=['GET'])
@scoped(scopes.VIEW_PROFILE, authorizer=user_is_owner)
def view_profile(user_id: str) -> Response:
    """User can view their account information."""
    data, code, headers = registration.view_profile(user_id, request.session)
    return render_template("accounts/profile.html", **data)


@blueprint.route('/<string:user_id>/profile/edit', methods=['GET', 'POST'])
@scoped(scopes.EDIT_PROFILE, authorizer=user_is_owner)
def edit_profile(user_id: str) -> Response:
    """User can update their account information."""
    data, code, headers = registration.edit_profile(request.method, user_id,
                                                    request.session,
                                                    request.form,
                                                    request.remote_addr)
    if code is status.HTTP_303_SEE_OTHER:
        target = url_for('ui.view_profile', user_id=user_id)
        response = make_response(redirect(target, code=code))
        set_cookies(response, data)
        return response
    content = render_template("accounts/edit_profile.html", **data)
    response = make_response(content, code, headers)
    return response


@blueprint.route('/login', methods=['GET', 'POST'])
@anonymous_only
def login() -> Response:
    """User can log in with username and password, or permanent token."""
    ip_address = request.remote_addr
    form_data = request.form

    data, code, headers = authentication.login(request.method,
                                               form_data, ip_address,
                                               request.next_page)

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code is status.HTTP_303_SEE_OTHER:
        # Set the session cookie.
        response = make_response(redirect(headers.get('Location'), code=code))
        set_cookies(response, data)
        return response

    # Form is invalid, or login failed.
    return render_template("accounts/login.html", **data), code


@blueprint.route('/logout', methods=['GET'])
def logout() -> Response:
    """Log out of arXiv."""
    session_cookie_key = current_app.config['SESSION_COOKIE_NAME']
    classic_cookie_key = current_app.config['CLASSIC_COOKIE_NAME']
    session_cookie = request.cookies.get(session_cookie_key, None)
    classic_cookie = request.cookies.get(classic_cookie_key, None)
    data, code, headers = authentication.logout(session_cookie, classic_cookie,
                                                request.next_page)

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code is status.HTTP_303_SEE_OTHER:
        response = make_response(redirect(headers.get('Location'), code=code))
        set_cookies(response, data)
        return response
    return redirect(url_for('get_login'), code=status.HTTP_302_FOUND)


@blueprint.route('/captcha', methods=['GET'])
@anonymous_only
def captcha() -> Response:
    """Provide the image for stateless stateless_captcha."""
    secret = current_app.config['CAPTCHA_SECRET']
    token = request.args.get('token')
    data, code, headers = captcha_image.get(token, secret, request.remote_addr)
    return send_file(data['image'], mimetype=data['mimetype']), code, headers
