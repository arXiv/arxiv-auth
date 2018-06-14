"""Provides scope-based authorization with JWT. For demo purposes only."""

from functools import wraps
from flask import request, g
from werkzeug.exceptions import BadRequest, Forbidden
from arxiv import status
from . import decode_authorization_token, DecodeError, get_auth_token


INVALID_TOKEN = {'reason': 'Invalid authorization token'}
INVALID_SCOPE = {'reason': 'Token not authorized for this action'}


def scoped(scope_required: str):
    """Generate a decorator to enforce scope authorization."""
    def protector(func):
        """Decorator that provides scope enforcement."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            """Check the authorization token before executing the method."""
            # Attach the encrypted token so that we can use it in subrequests.
            auth_data = request.environ.get('auth')
            if auth_data is None:
                raise BadRequest('Missing authentication credentials')
            scope = auth_data.get('scope')
            user = auth_data.get('user')
            client = auth_data.get('client')
            token = auth_data.get('token')

            if scope is None or user is None or token is None:
                raise BadRequest('Missing authentication credentials')

            if scope_required not in scope:
                raise Forbidden('Missing required scope')
            g.user = user
            g.client = client
            g.token = token
            return func(*args, **kwargs)
        return wrapper
    return protector
