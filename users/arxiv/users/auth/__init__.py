"""Provides tools for working with authenticated user/client sessions."""

from typing import Optional, Union
from datetime import datetime
import warnings
from pytz import UTC
from flask import Flask, request, Response, make_response, redirect, url_for
from werkzeug.http import parse_cookie
from werkzeug import MultiDict
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

        # If the legacy database is available, we should use it to authorize
        # the request.
        if legacy.is_configured():
            logger.debug('No session; attempting to get legacy session')
            response = self.detect_and_clobber_dupe_cookies()

            # Return that is anything other than None is treated as a response;
            # request handling stops here.
            if response is not None:
                return response
            session = self._get_legacy_session()

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

    def detect_and_clobber_dupe_cookies(self) -> Optional[Response]:
        """
        Detect and discard duplicate cookies.

        Legacy components have been known to generate dupe cookies, which
        causes all kinds of havoc. Here we check the request for duplicates
        of the session and permanent cookies and, if we find them, we blow
        them away and redirect back to /login.
        """
        # By default, werkzeug uses a dict-based struct that supports only a
        # single value per key. This isn't really up to speed with RFC 6265.
        # Luckily we can just pass in an alternate struct to parse_cookie()
        # that can cope with multiple values.
        raw_cookie = request.environ.get('HTTP_COOKIE', None)
        if raw_cookie is None:
            return None
        cookies = parse_cookie(raw_cookie, cls=MultiDict)
        classic_cookie_name = self.app.config['CLASSIC_COOKIE_NAME']
        perm_cookie_name = self.app.config['CLASSIC_PERMANENT_COOKIE_NAME']
        domain = self.app.config['AUTH_SESSION_COOKIE_DOMAIN']

        response = None     # If we return None, request is handled normally.
        now = datetime.now(UTC)
        for name in [classic_cookie_name, perm_cookie_name]:
            if len(cookies.getlist(name)) > 1:
                if response is None:
                    response = make_response(redirect(url_for('ui.login')))
                response.set_cookie(name, '', max_age=0, expires=now)
                response.set_cookie(name, '', max_age=0, expires=now,
                                    domain=domain.lstrip('.'))
                response.set_cookie(name, '', max_age=0, expires=now,
                                    domain=domain)
        return response
