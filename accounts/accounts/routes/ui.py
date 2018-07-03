"""Provides Flask integration for the external user interface."""

from flask import Blueprint, render_template, url_for, abort, request, \
    make_response, redirect, current_app, send_file
from arxiv import status
from arxiv.users.auth.decorators import scoped
from arxiv.users.auth import scopes
from arxiv.users import domain
from accounts.controllers import profile, captcha_image, registration, \
    authentication

from werkzeug.exceptions import BadRequest

blueprint = Blueprint('ui', __name__, url_prefix='/user')


def user_is_owner(session: domain.Session, user_id: str, **kwargs) -> bool:
    """Determine whether the authenticated user matches the requested user."""
    return session.user.user_id == user_id


@blueprint.before_request
def get_next_page() -> None:
    """Get the next page; this is where we'll redirect the user on success."""
    request.next_page = request.args.get('next_page', '')


@blueprint.route('/register', methods=['GET', 'POST'])
def register():     # type: ignore
    """Interface for creating new accounts."""
    captcha_secret = current_app.config['CAPTCHA_SECRET']
    ip_address = request.remote_addr
    data, code, headers = registration.register(request.method, request.form,
                                                captcha_secret, ip_address)
    session_cookie_key = current_app.config['SESSION_COOKIE_NAME']
    classic_cookie_key = current_app.config['CLASSIC_COOKIE_NAME']

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code == status.HTTP_303_SEE_OTHER:
        # Set the session cookie.
        session_cookie = data.pop('session_cookie')
        classic_cookie = data.pop('classic_cookie')
        response = make_response(redirect(headers.get('Location'), code=code))
        response.set_cookie(session_cookie_key, session_cookie)
        response.set_cookie(classic_cookie_key, classic_cookie)
        return response
    return render_template("accounts/register.html", **data)


@blueprint.route('/<string:user_id>/profile', methods=['GET'])
@scoped(scopes.VIEW_PROFILE, authorizer=user_is_owner)
def view_profile(user_id: str):
    """User can view their account information."""
    data, code, headers = profile.view_profile(user_id)
    return render_template("accounts/profile.html", **data)


@blueprint.route('/<string:user_id>/profile/edit', methods=['GET', 'POST'])
@scoped(scopes.EDIT_PROFILE, authorizer=user_is_owner)
def edit_profile(user_id: str):
    """User can update their account information."""
    data, code, headers = profile.edit_profile(request.method, user_id,
                                               request.form,
                                               request.remote_addr)
    return render_template("accounts/edit_profile.html", **data)


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    ip_address = request.remote_addr
    form_data = request.form

    data, code, headers = authentication.login(request.method,
                                               form_data, ip_address,
                                               request.next_page)
    session_cookie_key = current_app.config['SESSION_COOKIE_NAME']
    classic_cookie_key = current_app.config['CLASSIC_COOKIE_NAME']

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code == status.HTTP_303_SEE_OTHER:
        # Set the session cookie.
        session_cookie = data.pop('session_cookie')
        classic_cookie = data.pop('classic_cookie')
        response = make_response(redirect(headers.get('Location'), code=code))
        response.set_cookie(session_cookie_key, session_cookie)
        response.set_cookie(classic_cookie_key, classic_cookie)
        return response

    # Form is invalid, or login failed.
    return render_template("accounts/login.html", **data)


@blueprint.route('/logout', methods=['GET'])
def logout():  # type: ignore
    """Log out of arXiv."""
    session_cookie_key = current_app.config['SESSION_COOKIE_NAME']
    classic_cookie_key = current_app.config['CLASSIC_COOKIE_NAME']
    session_cookie = request.cookies.get(session_cookie_key, None)
    classic_cookie = request.cookies.get(classic_cookie_key, None)
    data, code, headers = authentication.logout(session_cookie, classic_cookie,
                                                request.next_page)

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code == status.HTTP_303_SEE_OTHER:
        response = make_response(redirect(headers.get('Location'), code=code))
        response.set_cookie(session_cookie_key, '', expires=0)
        response.set_cookie(classic_cookie_key, '', expires=0)
        return response
    return redirect(url_for('get_login'), code=status.HTTP_302_FOUND)


@blueprint.route('/captcha', methods=['GET'])
def captcha_image():
    """Provide the image for stateless stateless_captcha."""
    secret = current_app.config['CAPTCHA_SECRET']
    token = request.args.get('token')
    data, code, headers = captcha_image.get(token, secret, request.remote_addr)
    return send_file(data['image'], mimetype=data['mimetype']), code, headers
