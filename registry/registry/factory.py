"""Application factory for client registry app."""

from flask import Flask

from arxiv.base import Base
from arxiv.base.middleware import wrap
from arxiv.users import auth

from registry.routes import ui


def create_web_app() -> Flask:
    """Initialize and configure the accounts application."""
    app = Flask('accounts')
    app.config.from_pyfile('config.py')

    app.register_blueprint(ui.blueprint)
    Base(app)    # Gives us access to the base UI templates and resources.
    auth.Auth(app)  # Handless sessions and authn/z.
    wrap(app, [auth.middleware.AuthMiddleware])
    return app
