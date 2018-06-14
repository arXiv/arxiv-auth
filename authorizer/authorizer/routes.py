"""."""
from flask import Blueprint, current_app, request, jsonify
from werkzeug.exceptions import BadRequest
import jwt

from arxiv.base import logging
from .services import session_store

logger = logging.getLogger(__name__)

blueprint = Blueprint('authorizer', __name__, url_prefix='')


@blueprint.route('/auth', methods=['GET'])
def authorize():
    """Authorize the request."""
    try:
        cookie_name = current_app.config['SESSION_COOKIE_NAME']
    except KeyError as e:
        raise RuntimeError('Configuration error: missing parameter') from e

    # An authorization token may reside in either the Authorization header
    # or in a cookie (set at login).
    auth_header = request.headers.get('Authorization')
    auth_cookie = request.cookies.get(cookie_name)
    if auth_header:     # Try the header first.
        try:
            auth_token = auth_header.split()[1]
        except IndexError:
            logger.error('Authorization header malformed')
            raise BadRequest('Authorization header is malformed')
        logger.debug('Got auth token: %s', auth_token)
        claims = _authorize_from_header(auth_token)
    elif auth_cookie:   # Try the cookie second.
        logger.debug('Got auth cookie: %s', auth_cookie)
        claims = _authorize_from_cookie(auth_cookie)
    else:
        logger.error('Authorization token missing')
        raise BadRequest('No authorization token available')

    jwt_secret = current_app.config['JWT_SECRET']
    return jsonify({}), 200, {'Token': jwt.encode(claims, jwt_secret)}


def _authorize_from_cookie(auth_cookie: str) -> dict:
    """Authorize the request based on an auth cookie."""
    try:
        claims = session_store.get_user_session(auth_cookie)
    except session_store.InvalidToken:
        logger.error('Invalid user session token')
        raise BadRequest('Not a valid user session token')
    return claims


def _authorize_from_header(auth_token: str) -> dict:
    """Authorize the request based on an auth token."""
    try:
        claims = session_store.get_token_session(auth_token)
    except session_store.InvalidToken:
        logger.error('Invalid auth token')
        raise BadRequest('Not a valid auth token')
    return claims
