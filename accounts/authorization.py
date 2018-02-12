"""A minimal example of scope-based authorization with JWT."""

from functools import wraps
from flask import request, current_app, jsonify
import jwt

from typing import Any, Callable, Dict, Tuple

INVALID_TOKEN = {'reason': 'Invalid authorization token'}
INVALID_SCOPE = {'reason': 'Token not authorized for this action'}
HTTP_403_FORBIDDEN = 403

#TODO: many type clarifications needed here

def scoped(scope: str) -> Callable[[Any], Any]:
    """Generate a decorator to enforce scope authorization."""
    def protector(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        """Decorator that provides scope enforcement."""
        @wraps(func)
        def wrapper(*args: str, **kwargs: str) -> Tuple[Any, int, Dict[Any, Any]]:
            """Check the authorization token before executing the method."""
            secret = current_app.config.get('JWT_SECRET')
            encoded = request.headers.get('Authorization')
            try:
                decoded = jwt.decode(encoded, secret, algorithms=['HS256'])
            except jwt.exceptions.DecodeError: #type: ignore
                return jsonify(INVALID_TOKEN), HTTP_403_FORBIDDEN, {}
            if scope not in decoded.get('scope'): #type: ignore
                return jsonify(INVALID_SCOPE), HTTP_403_FORBIDDEN, {}
            return func(*args, **kwargs) #type: ignore
        return wrapper
    return protector
