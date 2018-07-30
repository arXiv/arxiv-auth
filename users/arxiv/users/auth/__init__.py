"""Provides tools for working with authenticated user/client sessions."""

from typing import Optional, Union
from flask import Flask, request
from . import decorators, middleware, scopes, tokens
from .. import domain, legacy

from arxiv.base import logging

logger = logging.getLogger(__name__)


class Auth(object):
    """
    Attaches session and authn/z information to the request.

    Intended for use in a Flask application factory, for example:

    .. code-block:: python

       from flask import Flask
       from arxiv.users.auth import Auth
       from someapp import routes


       def create_web_app() -> Flask:
          app = Flask('someapp')
          app.config.from_pyfile('config.py')
          Auth(app)   # Registers the base/UI blueprint.
          app.register_blueprint(routes.blueprint)    # Your blueprint.
       return app


    """

    def __init__(self, app: Optional[Flask] = None) -> None:
        """
        Initialize ``app`` with base blueprint.

        Parameters
        ----------
        app : :class:`Flask`

        """
        if app is not None:
            self.init_app(app)

    def _get_legacy_session(self) -> Optional[domain.Session]:
        """
        Attempt to load a legacy auth session.

        Returns
        -------
        :class:`domain.Session` or None

        """
        classic_cookie_key = self.app.config['CLASSIC_COOKIE_NAME']
        classic_cookie = request.cookies.get(classic_cookie_key, None)
        if classic_cookie is None:
            return None
        try:
            return legacy.sessions.load(classic_cookie)
        except legacy.exceptions.UnknownSession as e:
            logger.debug('No legacy session available')
        except legacy.exceptions.InvalidCookie as e:
            logger.debug('Invalid legacy cookie')
        except legacy.exceptions.SessionExpired as e:
            logger.debug('Legacy session is expired')
        return None

    def init_app(self, app: Flask) -> None:
        """
        Attach :meth:`.load_session` to the Flask app.

        Parameters
        ----------
        app : :class:`Flask`

        """
        self.app = app
        self.app.before_request(self.load_session)

    def load_session(self) -> None:
        """
        Look for an active session, and attach it to the request.

        The typical scenario will involve the
        :class:`.middleware.AuthMiddleware` unpacking a session token and
        adding it to the WSGI request environ. As a fallback, if the legacy
        database is available, this method will also attempt to load an
        active legacy session.
        """
        # Check the WSGI request environ for the ``session`` key, which
        # is where the auth middleware puts any unpacked auth information from
        # the request OR any exceptions that need to be raised withing the
        # request context.
        session: Optional[Union[domain.Session, Exception]] = \
            request.environ.get('session')

        # Middlware may have passed an exception, which needs to be raised
        # within the app/execution context to be handled correctly.
        if isinstance(session, Exception):
            logger.debug('Middleware passed an exception: %s', session)
            raise session

        # If we don't see a session, we may not be deployed behind a
        # gateway with an authorization service. If the legacy database
        # is available, we can try to use that as a fall-back.
        if not session and legacy.is_configured():
            logger.debug('No session; attempting to get legacy session')
            session = self._get_legacy_session()

        # Attach the session to the request so that other
        # components can access it easily.
        request.session = session
