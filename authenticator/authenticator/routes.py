"""."""
from flask import Blueprint, current_app, request, jsonify
from werkzeug.exceptions import BadRequest, Unauthorized
import jwt

from arxiv import status
import arxiv.users.domain
from arxiv.base import logging
from .services import sessions

logger = logging.getLogger(__name__)

blueprint = Blueprint('authenticator', __name__, url_prefix='')


@blueprint.route('/auth', methods=['GET'])
def authorize():
    """Authorize the request."""
    try:
        cookie_name = current_app.config['AUTH_SESSION_COOKIE_NAME']
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
        logger.error('Authorization token not found')
        return jsonify({}), status.HTTP_200_OK, {}

    jwt_secret = current_app.config['JWT_SECRET']
    headers = {'Authorization': jwt.encode(claims, jwt_secret)}
    return jsonify({}), status.HTTP_200_OK, headers


def _authorize_from_cookie(auth_cookie: str) -> dict:
    """Authorize the request based on an auth cookie."""
    try:
        session = sessions.load(auth_cookie)
    except (sessions.exceptions.InvalidToken,
            sessions.exceptions.ExpiredToken,
            sessions.exceptions.UnknownSession):
        logger.error('Invalid user session token')
        raise Unauthorized('Not a valid user session token')
    claims = arxiv.users.domain.to_dict(session)
    return claims


def _authorize_from_header(auth_token: str) -> dict:
    """Authorize the request based on an auth token."""
    try:
        session = sessions.load_by_id(auth_token)
    except (sessions.exceptions.InvalidToken,
            sessions.exceptions.ExpiredToken,
            sessions.exceptions.UnknownSession):
        logger.error('Invalid auth token')
        raise Unauthorized('Not a valid auth token')
    claims = arxiv.users.domain.to_dict(session)
    return claims
