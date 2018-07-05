"""Application factory for accounts app."""

from flask import Flask

from arxiv.base import Base
from arxiv.base.middleware import wrap
from arxiv.users import auth

from accounts.routes import ui
from accounts.services import sessions, legacy, users


def create_web_app() -> Flask:
    """Initialize and configure the accounts application."""
    app = Flask('accounts')
    app.config.from_pyfile('config.py')

    sessions.init_app(app)
    legacy.init_app(app)
    users.init_app(app)

    app.register_blueprint(ui.blueprint)
    Base(app)    # Gives us access to the base UI templates and resources.
    auth.Auth(app)  # Handless sessions and authn/z.
    wrap(app, [auth.middleware.AuthMiddleware])
    return app
