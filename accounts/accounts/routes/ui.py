"""Provides Flask integration for the external user interface."""

from flask import Blueprint, render_template, url_for, abort, request, \
    make_response, redirect, current_app
from arxiv import status
from accounts import controllers

blueprint = Blueprint('ui', __name__, url_prefix='/user')


@blueprint.before_request
def get_next_page() -> None:
    """Get the next page; this is where we'll redirect the user on success."""
    request.next_page = request.args.get(
        'next_page',
        current_app.config['DEFAULT_LOGIN_REDIRECT_URL']
    )


@blueprint.route('/register', methods=['GET', 'POST'])
def register():     # type: ignore
    """Interface for creating new accounts."""
    if request.method == 'POST':
        data, code, headers = controllers.post_register(request.form)
    else:
        data, code, headers = controllers.get_register()
    return render_template("accounts/register.html", **data)


@blueprint.route('/edit', methods=['GET', 'POST'])
def profile():
    """Interface for updating user profile."""
    if request.method == 'POST':
        data, code, headers = controllers.post_register(request.form)
    else:
        data, code, headers = controllers.get_register()
    return render_template("accounts/profile.html", **data)


@blueprint.route('/login', methods=['GET'])
def get_login():  # type: ignore
    """Get the login form."""
    data, code, headers = controllers.get_login()
    return render_template("accounts/login.html", **data)


@blueprint.route('/login', methods=['POST'])
def post_login():  # type: ignore
    """Handle POST request from login form."""
    ip_address = request.remote_addr
    form_data = request.form

    data, code, headers = controllers.post_login(form_data, ip_address,
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
    data, code, headers = controllers.logout(session_cookie, classic_cookie,
                                             request.next_page)

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code == status.HTTP_303_SEE_OTHER:
        response = make_response(redirect(headers.get('Location'), code=code))
        response.set_cookie(session_cookie_key, '', expires=0)
        response.set_cookie(classic_cookie_key, '', expires=0)
        return response
    return redirect(url_for('get_login'), code=status.HTTP_302_FOUND)
