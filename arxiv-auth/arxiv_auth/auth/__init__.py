"""Provides tools for working with authenticated user/client sessions."""

from typing import Optional, Union, Any, List
import warnings
import os

from flask import Flask, request, Response
from werkzeug.http import parse_cookie
from werkzeug.datastructures import MultiDict
from retry import retry

from .. import domain, legacy

import logging

from . import decorators

logger = logging.getLogger(__name__)


class Auth(object):
    """
    Attaches session and authentication information to the request.

    Set env var or `Flask.config` `ARXIV_AUTH_DEBUG` to True to get
    additional debugging in the logs. Only use this for short term debugging of
    configs. This may be used in produciton but should not be left on in production.

    Intended for use in a Flask application factory, for example:

    .. code-block:: python

       from flask import Flask
       from arxiv.users.auth import Auth
       from someapp import routes


       def create_web_app() -> Flask:
          app = Flask('someapp')
          app.config.from_pyfile('config.py')
          Auth(app)   # Registers the before_reques auth check
          app.register_blueprint(routes.blueprint)    # Your blueprint.
       return app


    """

    def __init__(self, app: Optional[Flask] = None) -> None:
        """
        Initialize ``app`` with `Auth`.

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

        if app.config.get('ARXIV_AUTH_DEBUG') or os.getenv('ARXIV_AUTH_DEBUG'):
            self.auth_debug()
            logger.debug("ARXIV_AUTH_DEBUG is set and auth debug messages to logging is turned on")

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
        """Look for an active session, and attach it to the request.

        This is run before each Flask reqeust if :class:`arxiv_auth.auth.Auth`
        is setup on the `Flask` app.

        The typical scenario will involve the
        :class:`.middleware.AuthMiddleware` unpacking a session token and
        adding it to the WSGI request environ. As a fallback, if the legacy
        database is available, this method will also attempt to load an
        active legacy session.

        As of 2023-04 this only chekcs for the legacy `tapir_session`
        cookie. Use of the NG `ARXIVNG_SESSION_ID` has never been implemented in
        this class.
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
            auth = self.first_valid(self.legacy_cookies())
        else:
            logger.warning('No legacy DB, will not check tapir auth.')

        # Attach obj to the request for use by other components
        request.auth = auth
        return None


    def first_valid(self, cookies: List[str]) -> Optional[domain.Session]:
        """First valid legacy session or None if there are none."""
        first =  next(filter(bool,
                             map(self._get_legacy_session,
                                 cookies)), None)

        if first is None:
            logger.debug("Out of %d cookies, no good legacy cookie found", len(cookies))
        else:
            logger.debug("Out of %d cookies, using first good legacy cookie", len(cookies))

        return first

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

    def auth_debug(self) -> None:
        """Sets several auth loggers to DEBUG.

        This is useful to get an idea of what is going on with auth."""
        logger.setLevel(logging.DEBUG)
        legacy.sessions.logger.setLevel(logging.DEBUG)
        legacy.authenticate.logger.setLevel(logging.DEBUG)
