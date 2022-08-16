"""Provides tools for working with authenticated user/client sessions."""

from typing import Optional, Union, Any, List
import warnings

from flask import Flask, request, Response
from werkzeug.http import parse_cookie
from werkzeug.datastructures import MultiDict
from retry import retry

from .. import domain, legacy

from arxiv.base import logging

from . import decorators

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

    @retry(legacy.exceptions.Unavailable, tries=3, delay=0.5, backoff=2)
    def _get_legacy_session(self,
                            cookie_value: str) -> Optional[domain.Session]:
        """
        Attempt to load a legacy auth session.

        Returns
        -------
        :class:`domain.Session` or None

        """
        if cookie_value is None:
            return None
        try:
            with legacy.transaction():
                return legacy.sessions.load(cookie_value)
        except legacy.exceptions.UnknownSession as e:
            logger.debug('No legacy session available: %s', e)
        except legacy.exceptions.InvalidCookie as e:
            logger.debug('Invalid legacy cookie: %s', e)
        except legacy.exceptions.SessionExpired as e:
            logger.debug('Legacy session is expired: %s', e)
        return None

    def init_app(self, app: Flask) -> None:
        """
        Attach :meth:`.load_session` to the Flask app.

        Parameters
        ----------
        app : :class:`Flask`

        """
        self.app = app
        app.config['arxiv_auth.Auth'] = self
        legacy.init_app(app)
        self.app.before_request(self.load_session)
        self.app.config.setdefault('DEFAULT_LOGOUT_REDIRECT_URL',
                                   'https://arxiv.org')
        self.app.config.setdefault('DEFAULT_LOGIN_REDIRECT_URL',
                                   'https://arxiv.org')

        @self.app.teardown_request
        def teardown_request(exception: Optional[Exception]) -> None:
            session = legacy.current_session()
            if exception:
                session.rollback()
            session.remove()

        @self.app.teardown_appcontext
        def teardown_appcontext(*args: Any, **kwargs: Any) -> None:
            session = legacy.current_session()
            session.rollback()
            session.remove()

    def load_session(self) -> Optional[Response]:
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
        # use legacy DB to authorize request if available
        if legacy.is_configured():
            logger.debug('No session; attempting to get legacy from cookies')
            session = self.first_valid(self.legacy_cookies())

        # Attach the session to the request so that other
        # components can access it easily.
        if self.app.config.get('AUTH_UPDATED_SESSION_REF'):
            request.auth = session
        else:
            # This clobbers the built-in Flask session interface. This is a
            # design flaw that's blocking other work. This is deprecated and
            # will be removed in 0.4.1.
            warnings.warn(
                "Accessing the authenticated session via request.auth is"
                " deprecated, and will be removed in 0.4.1. Use request.auth"
                " instead. ARXIVNG-1920.",
                DeprecationWarning
            )
            request.session = session
        return None

    def first_valid(self, cookies: List[str]) -> Optional[domain.Session]:
        """First valid legacy session or None if there are none."""
        return next(filter(bool,
                           map(self._get_legacy_session,
                               cookies)),
                    None)

    def legacy_cookies(self) -> List[str]:
        """Gets list of legacy cookies.

        Duplicate cookies occur due to the browser sending both the
        cookies for both arxiv.org and sub.arxiv.org. If this is being
        served at sub.arxiv.org, there is no response that will cause
        the browser to alter its cookie store for arxiv.org. Duplicate
        cookies must be handled gracefully to for the domain and
        subdomain to coexist.

        The standard way to avoid this problem is to append part of
        the domain's name to the cookie key but this needs to work
        even if the configuration is not ideal.

        """
        # By default, werkzeug uses a dict-based struct that supports only a
        # single value per key. This isn't really up to speed with RFC 6265.
        # Luckily we can just pass in an alternate struct to parse_cookie()
        # that can cope with multiple values.
        raw_cookie = request.environ.get('HTTP_COOKIE', None)
        if raw_cookie is None:
            return []
        cookies = parse_cookie(raw_cookie, cls=MultiDict)
        return cookies.getlist(self.app.config['CLASSIC_COOKIE_NAME'])
