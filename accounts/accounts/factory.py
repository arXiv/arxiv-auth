"""Application factory for accounts app."""

from flask import Flask
from flask_s3 import FlaskS3

from arxiv.base import Base
from arxiv.base.middleware import wrap

from arxiv_auth import auth
from arxiv_auth.auth.middleware import AuthMiddleware

from accounts.routes import ui

from arxiv_auth.auth.sessions import SessionStore
from arxiv_auth.legacy.util import init_app as legacy_init_app
from arxiv_auth.legacy.util import create_all as legacy_create_all

s3 = FlaskS3()


def create_web_app() -> Flask:
    """Initialize and configure the accounts application."""
    app = Flask('accounts')
    app.config.from_pyfile('config.py')

    # Don't set SERVER_NAME, it switches flask blueprints to be
    # subdomain aware.  Then each blueprint will only be served on
    # it's subdomain.  This doesn't work with mutliple domains like
    # webN.arxiv.org and arxiv.org. We need to handle both names so
    # that individual nodes can be addresed for diagnotics. Not
    # setting this will allow the flask app to handle both
    # https://web3.arxiv.org/login and https://arxiv.org/login. If
    # this gets set paths that should get handled by the app will 404
    # when the request is made with a HOST that doesn't match
    # SERVER_NAME.

    # The flask docs say: SERVER_NAME: the name and port number of the
    # server. Required for subdomain support (e.g.: 'myapp.dev:5000')
    # Note that localhost does not support subdomains so setting this
    # to “localhost” does not help. Setting a SERVER_NAME also by
    # default enables URL generation without a request context but with
    # an application context.
    app.config['SERVER_NAME'] = None

    SessionStore.init_app(app)
    legacy_init_app(app)

    app.register_blueprint(ui.blueprint)
    Base(app)    # Gives us access to the base UI templates and resources.
    auth.Auth(app)  # Handless sessions and authn/z.
    s3.init_app(app)

    middleware = [AuthMiddleware]
    wrap(app, middleware)

    if app.config['CREATE_DB']:
        with app.app_context():
            legacy_create_all()

    return app
