"""Middleware for decoding JWTs on requests. For demo purposes only."""

import os
from typing import Callable, Iterable, Tuple
import jwt

from werkzeug.exceptions import Unauthorized, InternalServerError

from arxiv.base.middleware import BaseMiddleware
from arxiv.base import logging

from . import tokens
from .exceptions import InvalidToken, ConfigurationError, MissingToken
from .. import domain

logger = logging.getLogger(__name__)

WSGIRequest = Tuple[dict, Callable]


class AuthMiddleware(BaseMiddleware):
    """
    Middleware to handle auth information on requests.

    Before the request is handled by the application, the ``Authorization``
    header is parsed for an encrypted JWT. If successfully decrypted,
    information about the user and their authorization scope is attached
    to the request.

    This can be accessed in the application via
    ``flask.request.environ['auth']``.  If Authorization header was not
    included, or if the JWT could not be decrypted, then that value will be
    ``None``.
    """

    def before(self, environ: dict, start_response: Callable) -> WSGIRequest:
        """Decode and unpack the auth token on the request."""
        environ['session'] = None      # Create the session key, at a minimum.
        environ['token'] = None
        token = environ.get('HTTP_AUTHORIZATION')    # We may not have a token.
        if token is None:
            logger.info('No auth token')
            return environ, start_response

        # The token secret should be set in the WSGI environ, or in os.environ.
        secret = environ.get('JWT_SECRET', os.environ.get('JWT_SECRET'))
        if secret is None:
            raise ConfigurationError('Missing decryption token')

        try:
            # Try to verify the token in the Authorization header, and attach
            # the decoded session data to the request.
            environ['session']: domain.Session = tokens.decode(token, secret)

            # Attach the encrypted token so that we can use it in subrequests.
            environ['token'] = token
        except InvalidToken as e:   # Let the application decide what to do.
            logger.error('Auth token not valid')
            environ['session'] = Unauthorized('Invalid auth token')
        except Exception as e:
            logger.error(f'Unhandled exception: {e}')
            environ['session'] = InternalServerError(f'Unhandled: {e}')
        return environ, start_response
