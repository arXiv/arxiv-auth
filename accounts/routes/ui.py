"""Provides routes for the external user interface."""

from flask import Blueprint, render_template, url_for, abort, request, \
    make_response, redirect
from arxiv import status
from accounts import authorization, controllers


blueprint = Blueprint('ui', __name__, url_prefix='/user')


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
    data, code, headers = controllers.post_login(form_data, ip_address)

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code == status.HTTP_303_SEE_OTHER:
        # Set the session cookie.
        session_id = data.pop('session_id')
        tapir_session_id = data.pop('tapir_session_id')
        response = make_response(redirect(headers.get('Location'), code=code))
        response.set_cookie('ARXIVNG_SESSION_ID', session_id)
        response.set_cookie('tapir_session', tapir_session_id)
        return response

    # Form is invalid, or login failed.
    return render_template("accounts/login.html", **data)


@blueprint.route('/logout', methods=['GET'])
def logout():  # type: ignore
    """Log out of arXiv."""
    session_id = request.cookies.get('ARXIVNG_SESSION_ID', None)
    data, code, headers = controllers.logout(session_id)

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code == status.HTTP_303_SEE_OTHER:
        response = make_response(redirect(headers.get('Location'), code=code))
        response.set_cookie('ARXIVNG_SESSION_ID', '', expires=0)
        response.set_cookie('tapir_session', '', expires=0)
        return response
    return redirect(url_for('get_login'), code=status.HTTP_302_FOUND)
