"""Web Server Gateway Interface entry-point."""

from registry.factory import create_web_app
import os


def application(environ, start_response):    # type: ignore
    """WSGI application factory."""
    for key, value in environ.items():
        os.environ[key] = str(value)
    app = create_web_app()
    return app(environ, start_response)
