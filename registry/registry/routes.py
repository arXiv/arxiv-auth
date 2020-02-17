"""Provides Flask integration for the external user interface."""

from typing import Any, Callable
from datetime import datetime, timedelta
from functools import wraps
from pytz import timezone, UTC

from werkzeug.urls import Href, url_encode, url_parse, url_unparse, url_encode
from flask import Blueprint, render_template, url_for, abort, request, \
    make_response, redirect, current_app, send_file, Response, redirect

from arxiv import status
from arxiv.users.auth.decorators import scoped
from arxiv.users.auth import scopes
from arxiv.users import domain
from arxiv.base import logging

from werkzeug.exceptions import BadRequest

from . import oauth2

EASTERN = timezone('US/Eastern')

logger = logging.getLogger(__name__)

blueprint = Blueprint('oauth', __name__, url_prefix='')


def redirect_to_login(*args, **kwargs):
    """Send the user to log in, with a pointer back to the current URL."""
    query = url_encode({'next_page': request.url})
    parts = url_parse(url_for('login')).replace(query=query)
    return redirect(url_unparse(parts))


@blueprint.route('/token', methods=['POST'])
def issue_token() -> Response:
    """Client authentication endpoint."""
    logger.debug('Request to issue token with params %s', request.form)
    server = current_app.server
    logger.debug('Got OAuth2 server %s', id(server))
    response = server.create_token_response()
    logger.debug('Generated response %s', response)
    return response


@blueprint.route('/authorize', methods=['GET', 'POST'])
@scoped(unauthorized=redirect_to_login)
def authorize():
    """User-facing endpoint for authorization code (three-legged) workflow."""
    server = current_app.server
    if request.method == 'GET':
        try:
            grant_user = oauth2.OAuth2User(request.auth.user)
            grant = server.validate_consent_request(end_user=grant_user)
            logger.debug('Granted user')
            return render_template(
                'registry/authorize.html',
                grant=grant,
                user=request.auth.user
            )
        except oauth2.OAuth2Error as ex:
            logger.debug('Got OAuth2Error: %s', ex)
            raise BadRequest(str(ex)) from ex
    elif request.method == 'POST':
        if request.form['confirm'] == 'ok':
            logger.debug('User authorizes client')
            grant_user = oauth2.OAuth2User(request.auth.user)
        else:
            logger.debug('User has not authorized client')
            grant_user = None
        return server.create_authorization_response(grant_user=grant_user)
