"""Application factory for accounts app."""

from flask import Flask

from arxiv.base import Base

from accounts.routes import ui
from accounts.services import session_store, classic_session_store, users
from accounts.encode import ISO8601JSONEncoder


def create_web_app() -> Flask:
    """Initialize and configure the accounts application."""
    app = Flask('accounts')
    app.config.from_pyfile('config.py')
    app.json_encoder = ISO8601JSONEncoder

    session_store.init_app(app)
    classic_session_store.init_app(app)
    users.init_app(app)

    Base(app)    # Gives us access to the base UI templates and resources.
    app.register_blueprint(ui.blueprint)

    return app
