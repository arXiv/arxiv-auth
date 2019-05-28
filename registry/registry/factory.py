"""Application factory for client registry app."""

from flask import Flask

from arxiv import vault
from arxiv.base import Base
from arxiv.base.middleware import wrap
from arxiv.users import auth

# from registry.routes import ui
from registry import filters
from registry.services import datastore, SessionStore
from registry.routes import blueprint
from . import oauth2


def create_web_app() -> Flask:
    """Initialize and configure the accounts application."""
    app = Flask('registry')
    app.config.from_pyfile('config.py')

    # app.register_blueprint(ui.blueprint)

    datastore.init_app(app)
    SessionStore.init_app(app)

    Base(app)    # Gives us access to the base UI templates and resources.
    auth.Auth(app)  # Handless sessions and authn/z.
    oauth2.init_app(app)
    app.register_blueprint(blueprint)

    middleware = [auth.middleware.AuthMiddleware]
    if app.config['VAULT_ENABLED']:
        middleware.insert(0, vault.middleware.VaultMiddleware)
    wrap(app, middleware)
    if app.config['VAULT_ENABLED']:
        app.middlewares['VaultMiddleware'].update_secrets({})

    app.jinja_env.filters['scope_label'] = filters.scope_label

    if app.config['CREATE_DB']:
        with app.app_context():
            datastore.create_all()

    return app
