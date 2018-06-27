"""Provides scope-based authorization with JWT. For demo purposes only."""

from typing import Optional, Union, Callable, Any
from functools import wraps
from flask import request, current_app
from werkzeug.exceptions import BadRequest, Forbidden, Unauthorized
from arxiv import status

from .. import domain, legacy

INVALID_TOKEN = {'reason': 'Invalid authorization token'}
INVALID_SCOPE = {'reason': 'Token not authorized for this action'}
# with self.app.app_context():
#     if legacy.is_configured():
#         cookie_key = self.app.config['CLASSIC_COOKIE_NAME']


# if classic.database_is_configured():
#     try:
#         environ['user'] = User(**classic.verify_session(environ))
#     except classic.DatabaseNotAvailable as e:
#         logger.error('Classic database is not available')
#     except classic.InvalidSession as e:
#         logger.error('Classic session is not valid')


def _get_legacy_session() -> Optional[domain.Session]:
    """Attempt to load a legacy auth session."""
    classic_cookie_key = current_app.config['CLASSIC_COOKIE_NAME']
    classic_cookie = request.cookies.get(classic_cookie_key, None)
    return legacy.load(classic_cookie)


def scoped(required: str, authorizer: Optional[Callable] = None) -> Callable:
    """
    Generate a decorator to enforce authorization requirements.

    Parameters
    ----------
    required : str
        The scope required on a user or client session in order use the
        decorated route. See :mod:`arxiv.users.auth.scopes`.
    authorizer : function
        In addition, an authorizer function may be passed to provide more
        specific authorization checks. For example, this function may check
        that the requesting user is the owner of a resource. Should have the
        signature: ``(session: domain.Session) -> bool``. If it returns
        ``False``, an :class:`.Forbidden` exception is raised.

    Returns
    -------
    function
        A decorator that enforces the required scope and calls the (optionally)
        provided authorizer.

    """
    def protector(func: Callable) -> Callable:
        """Decorator that provides scope enforcement."""
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            Check the authorization token before executing the method.

            Will also raise exceptions passed by the auth middleware.

            Raises
            ------
            :class:`.Unauthorized`
                Raised when session data is not available.
            :class:`.Forbidden`
                Raised when the session has insufficient auth scope, or the
                provided authorizer returns ``False``.

            """
            session: Optional[Union[domain.Session, Exception]] = \
                request.environ.get('session')

            # Middlware may have passed an exception, which needs to be raised
            # within the app/execution context to be handled correctly.
            if isinstance(session, Exception):
                raise session

            # If we don't see a session, we may not be deployed behind a
            # gateway with an authorization service. If the legacy database
            # is available, we can try to use that as a fall-back.
            if not session and legacy.is_configured():
                session = _get_legacy_session()

            # Use of the decorator implies that an auth session ought to be
            # present. So we'll complain here if it's not.
            if not session or not (session.user or session.client):
                raise Unauthorized('Not a valid session')

            # Check the required scopes.
            if required not in session.authorizations.scopes:
                raise Forbidden('Not authorized for this route')

            # Call the provided authorizer function.
            if authorizer and not authorizer(session):
                raise Forbidden('Insufficient privileges')

            return func(*args, **kwargs)
        return wrapper
    return protector
