"""Provides Flask integration for the external user interface."""

from typing import Any, Callable
from datetime import datetime, timedelta
from functools import wraps
from pytz import timezone
from flask import Blueprint, render_template, url_for, abort, request, \
    make_response, redirect, current_app, send_file, Response
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


@blueprint.route('/token', methods=['POST'])
def issue_token() -> Response:
    """Client authentication endpoint."""
    logger.debug('Request to issue token')
    server = current_app.server
    logger.debug('Got OAuth2 server %s', id(server))
    response = server.create_token_response()
    logger.debug('Generated response %s', response)
    return response
