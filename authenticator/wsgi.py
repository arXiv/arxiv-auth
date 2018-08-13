"""Web Server Gateway Interface entry-point."""

from authenticator.factory import create_app
import os


def application(environ, start_response):
    """WSGI application factory."""
    for key, value in environ.items():
        os.environ[key] = str(value)
    return create_app()(environ, start_response)
