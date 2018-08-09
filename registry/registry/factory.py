"""Application factory for client registry app."""

from flask import Flask

from arxiv.base import Base
from arxiv.base.middleware import wrap
from arxiv.users import auth

# from registry.routes import ui
from registry.services import datastore, sessions
from registry.routes import blueprint
from . import oauth2


def create_web_app() -> Flask:
    """Initialize and configure the accounts application."""
    app = Flask('registry')
    app.config.from_pyfile('config.py')

    # app.register_blueprint(ui.blueprint)

    datastore.init_app(app)
    sessions.init_app(app)

    Base(app)    # Gives us access to the base UI templates and resources.
    auth.Auth(app)  # Handless sessions and authn/z.
    oauth2.init_app(app)
    app.register_blueprint(blueprint)
    wrap(app, [auth.middleware.AuthMiddleware])
    datastore.create_all()
    return app
