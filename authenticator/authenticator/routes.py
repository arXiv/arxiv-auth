"""."""
from flask import Blueprint, current_app, request, jsonify
import traceback
from werkzeug.exceptions import BadRequest, Unauthorized
import jwt

from arxiv import status
import arxiv.users.domain
from arxiv.base import logging
from .services.sessions import InvalidToken, ExpiredToken, UnknownSession
from .services import SessionStore

logger = logging.getLogger(__name__)

blueprint = Blueprint('authenticator', __name__, url_prefix='')


@blueprint.route('/auth', methods=['GET'])
def authenticate():
    """Authenticate the request."""
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
            logger.error('Auth header malformed')
            raise BadRequest('Auth header is malformed')
        logger.debug('Got auth token: %s', auth_token)
        try:
            jwt_encoded = _authenticate_from_header(auth_token)
        except Unauthorized as e:
            raise e
        except Exception as e:
            logger.error('Unhandled exception: %s', e)
            logger.error(traceback.format_exc())
            return jsonify({}), status.HTTP_200_OK, {}
    elif auth_cookie:   # Try the cookie second.
        logger.debug('Got auth cookie: %s', auth_cookie)
        try:
            jwt_encoded = _authenticate_from_cookie(auth_cookie)
        except Unauthorized as e:
            raise e
        except Exception as e:
            logger.error('Unhandled exception: %s', e)
            logger.error(traceback.format_exc())
            return jsonify({}), status.HTTP_200_OK, {}
    else:
        logger.error('Auth token not found')
        return jsonify({}), status.HTTP_200_OK, {}

    # jwt_secret = current_app.config['JWT_SECRET']
    headers = {'Authorization': jwt_encoded}
    return jsonify({}), status.HTTP_200_OK, headers


def _authenticate_from_cookie(auth_cookie: str) -> str:
    """Authenticate the request based on an auth cookie."""
    sessions = SessionStore.current_session()
    try:
        session_token = sessions.load(auth_cookie, decode=False)
    except (InvalidToken, ExpiredToken, UnknownSession) as e:
        logger.error('Invalid user session token')
        raise Unauthorized('Not a valid user session token') from e
    # claims = arxiv.users.domain.to_dict(session)
    # return claims
    return session_token


def _authenticate_from_header(auth_token: str) -> str:
    """Authenticate the request based on an auth token."""
    sessions = SessionStore.current_session()
    try:
        session_token = sessions.load_by_id(auth_token, decode=False)
    except (InvalidToken, ExpiredToken, UnknownSession) as e:
        logger.error('Invalid auth token: %s: %s', type(e), e)
        raise Unauthorized('Not a valid auth token') from e
    return session_token
    # claims = arxiv.users.domain.to_dict(session)
    # return claims
