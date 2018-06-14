from typing import Tuple, Callable, Optional, NamedTuple

import jwt

from arxiv.base import BaseMiddleware, logging
from . import classic


logger = logging.getLogger(__name__)


class User(NamedTuple):
    """."""


class InvalidToken(ValueError):
    """Token in request is not valid."""


class MissingToken(ValueError):
    """No token found in request."""


class ConfigurationError(RuntimeError):
    """The application is not configured correctly."""


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

    def before(self, environ: dict, start_response: Callable) \
            -> Tuple[dict, Callable]:
        environ['user'] = None
        # Try to verify the token in the Authorzation header first.
        try:
            token, decoded = self._verify_token(environ)
            environ['auth'] = {
                'scope': decoded.get('scope', []),
                'user': decoded.get('user'),
                'client': decoded.get('client'),
                'token': token
            }
        except InvalidToken as e:   # Might be forged!
            logger.error('Auth token not valid')
        except MissingToken as e:
            logger.info('No auth token; attempting to use classic session')
            # If we don't see a token, we're probably not deployed behind a
            # gateway with an authorization service. If the legacy database
            # is available, we can try to use that as a fall-back.
            if classic.database_is_configured():
                try:
                    environ['user'] = User(**classic.verify_session(environ))
                except classic.DatabaseNotAvailable as e:
                    logger.error('Classic database is not available')
                except classic.InvalidSession as e:
                    logger.error('Classic session is not valid')
        except Exception as e:
            logger.error(f'Unhandled exception: {e}')
        return environ, start_response

    def _verify_token(self, environ: dict) -> Tuple[str, dict]:
        try:
            token = environ['AUTHORIZATION']
        except KeyError as e:
            raise MissingToken('Authorization token not found') from e
        try:
            secret = environ['JWT_SECRET']
        except KeyError as e:
            raise ConfigurationError('Missing decryption token')
        try:
            data: dict = jwt.decode(token, secret, algorithms=['HS256'])
        except jwt.exceptions.DecodeError as e:
            raise InvalidToken('Not a valid token') from e
        return token, data
