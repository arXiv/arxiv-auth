"""Application factory for a test auth app."""

from flask import Flask

from arxiv.base import Base
from arxiv.base.middleware import wrap

from arxiv_auth import auth
from arxiv_auth.auth.middleware import AuthMiddleware

from arxiv_auth.auth.sessions import SessionStore
from arxiv_auth.legacy.util import init_app as legacy_init_app
from arxiv_auth.legacy.util import create_all as legacy_create_all


def create_web_app(create_db=False) -> Flask:
    """Initialize and configure test auth application.

    Similar to what is in accounts/acounts/factory.py
    """
    app = Flask('test_auth_app')

    SessionStore.init_app(app)
    legacy_init_app(app)

    Base(app)
    auth.Auth(app)

    middleware = [AuthMiddleware]
    wrap(app, middleware)

    if create_db:
        with app.app_context():
            legacy_create_all()

    return app
