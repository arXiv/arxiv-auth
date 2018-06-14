"""Interface for authorizing user/client sessions."""

import json
from datetime import datetime

from flask import current_app
import redis
import jwt

from arxiv.base import logging

logger = logging.getLogger(__name__)


class InvalidToken(RuntimeError):
    """Raised when a passed token is malformed or otherwise invalid."""


class ConfigurationError(RuntimeError):
    """Raised when a required service parameter is missing."""


def _get_redis() -> redis.StrictRedis:
    """Get a new connection to Redis."""
    try:
        host = current_app.config['REDIS_HOST']
        port = current_app.config['REDIS_PORT']
        db = current_app.config['REDIS_DATABASE']
    except KeyError as e:
        raise ConfigurationError('Missing required config parameter') from e
    return redis.StrictRedis(host=host, port=port, db=db)


def _get_secret() -> str:
    try:
        return current_app.config['JWT_SECRET']
    except KeyError as e:
        raise ConfigurationError('Missing required config parameter') from e


def get_user_session(session_token: str) -> dict:
    """
    Get a session from a user session token.

    Parameters
    ----------
    session_token : str
        An encrypted JWT passed by the client.

    Returns
    -------
    dict
        Claims associated with the session, including auth scope and user
        identity.

    Raises
    ------
    InvalidToken

    """
    r = _get_redis()
    try:
        payload = jwt.decode(session_token, _get_secret())
        session_id = payload['session_id']
        user_id = payload['user_id']
        nonce = payload['nonce']
    except (KeyError, jwt.exceptions.DecodeError) as e:
        raise InvalidToken('Token payload malformed') from e

    try:
        data = json.loads(r.get(session_id))
    except json.decoder.JSONDecodeError:
        raise InvalidToken('Invalid or corrupted session')

    # Make sure that the session has not expired/been invalidated.
    now = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
    expires = data.get('end_time')
    if expires and expires <= now:
        raise InvalidToken('Session has expired')

    if user_id != data['user_id'] or nonce != data['nonce']:
        raise InvalidToken('Invalid token; likely a forgery')
    data.pop('nonce')   # No need to put this in the claims.
    return data


# Keeping this separate for now, in case mechanisms/formats change. We may
# be able to merge this with `get_user_session` in the end.
def get_token_session(session_token: str) -> dict:
    """
    Get a session from a bearer token.

    Parameters
    ----------
    session_token : str
        An encrypted JWT passed by the client.

    Returns
    -------
    dict
        Claims associated with the session, including auth scope and client
        identity.

    Raises
    ------
    InvalidToken

    """
    r = _get_redis()
    try:
        payload = jwt.decode(session_token, _get_secret())
        session_id = payload['session_id']
        client_id = payload['client_id']
        nonce = payload['nonce']
    except (KeyError, jwt.exceptions.DecodeError) as e:
        logger.error(f'Token payload malformed: {e}')
        raise InvalidToken('Token payload malformed') from e

    try:
        data = json.loads(r.get(session_id))
    except json.decoder.JSONDecodeError:
        logger.error('Invalid or corrupted session')
        raise InvalidToken('Invalid or corrupted session')

    # The nonce was generated when the session was created.
    if client_id != data['client_id'] or nonce != data['nonce']:
        logger.error('Invalid token; likely a forgery')
        raise InvalidToken('Invalid token; likely a forgery')

    # May be a three-legged token, in which case the user_id should be present.
    if 'user_id' in payload and payload['user_id'] != data['user_id']:
        logger.error('Invalid token; likely a forgery')
        raise InvalidToken('Invalid token; likely a forgery')

    # Make sure that the session has not expired/been invalidated.
    now = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
    expires = data.get('end_time')
    if expires and expires <= now:
        logger.error('Session has expired')
        raise InvalidToken('Session has expired')

    data.pop('nonce')   # No need to put this in the claims.
    return data
