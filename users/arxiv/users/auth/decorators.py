"""
Scope-based authorization of user/client requests.

This module provides :func:`scoped`, a decorator factory used to protect Flask
routes for which authorization is required. This is done by specifying a
required authorization scope (see :mod:`arxiv.users.auth.scopes`) and/or by
providing a custom authorizer function.

Using :func:`scoped` with an authorizer function allows you to define
application-specific authorization logic on a per-request basis without adding
complexity to request controllers. The call signature of the authorizer
function should be: ``(session: domain.Session, *args, **kwargs) -> bool``,
where `*args` and `**kwargs` are the positional and keyword arguments,
respectively, passed by Flask to the decorated route function (e.g. the
URL parameters).

Here's an example of how you might use this in a Flask application:

.. code-block:: python

   from arxiv.users.auth.decorators import scoped
   from arxiv.users.auth import scopes
   from arxiv.users import domain


   def is_owner(session: domain.Session, user_id: str, **kwargs) -> bool:
       '''Check whether the authenticated user matches the requested user.'''
       return session.user.user_id == user_id


   @blueprint.route('/<string:user_id>/profile', methods=['GET'])
   @scoped(scopes.EDIT_PROFILE, authorizer=user_is_owner)
   def edit_profile(user_id: str):
       '''User can update their account information.'''
       data, code, headers = profile.get_profile(user_id)
       return render_template('accounts/profile.html', **data)


When the decorated route function is called...

- If no session is available from either the middleware or the legacy database,
  an :class:`Unauthorized` exception is raised.
- If a required scope was provided, the session is checked for the presence of
  that scope.
- If an authorization function was provided, the function is called.
- Session data is added directly to the Flask request object as
  ``request.session``, for ease of access elsewhere in the application.
- Finally, if no exceptions have been raised, the route is called with the
  original parameters.

"""

from typing import Optional, Union, Callable, Any
from functools import wraps
from flask import request
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden
from arxiv import status
from arxiv.base import logging
from .. import domain

INVALID_TOKEN = {'reason': 'Invalid authorization token'}
INVALID_SCOPE = {'reason': 'Token not authorized for this action'}


logger = logging.getLogger(__name__)


def scoped(required: Optional[str] = None,
           authorizer: Optional[Callable] = None) -> Callable:
    """
    Generate a decorator to enforce authorization requirements.

    Parameters
    ----------
    required : str
        The scope required on a user or client session in order use the
        decorated route. See :mod:`arxiv.users.auth.scopes`. If not provided,
        no scope will be enforced.
    authorizer : function
        In addition, an authorizer function may be passed to provide more
        specific authorization checks. For example, this function may check
        that the requesting user is the owner of a resource. Should have the
        signature: ``(session: domain.Session, *args, **kwargs) -> bool``.
        ``*args`` and ``**kwargs`` are the parameters passed to the decorated
        function. If the authorizer returns ``False``, an :class:`.`
        exception is raised.

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
            :class:`.`
                Raised when the session has insufficient auth scope, or the
                provided authorizer returns ``False``.

            """
            session = request.session
            # Use of the decorator implies that an auth session ought to be
            # present. So we'll complain here if it's not.
            if not session or not (session.user or session.client):
                logger.debug('No valid session; aborting')
                raise Unauthorized('Not a valid session')  # type: ignore

            # Check the required scopes.
            if required and (session.authorizations is None
                             or required not in session.authorizations.scopes):
                logger.debug('Session is not authorized for %s', required)
                raise Forbidden('Access denied')  # type: ignore

            # Call the provided authorizer function.
            if authorizer and not authorizer(session, *args, **kwargs):
                logger.debug('Authorizer retured negative result')
                raise Forbidden('Access denied')  # type: ignore

            logger.debug('Request is authorized, proceeding')
            return func(*args, **kwargs)
        return wrapper
    return protector
