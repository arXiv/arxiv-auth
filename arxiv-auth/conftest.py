import pytest

from flask import Flask
from sqlalchemy import create_engine

from arxiv.base import Base
from arxiv.base.middleware import wrap
from arxiv.db.models import reconfigure_db

from arxiv_auth.auth.sessions import SessionStore
from arxiv_auth.legacy.util import create_all as legacy_create_all
from arxiv_auth.auth import Auth
from arxiv_auth.auth.middleware import AuthMiddleware


@pytest.fixture()
def app():

    app = Flask('test_auth_app')
    app.config['CLASSIC_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['CLASSIC_SESSION_HASH'] = f'fake set in {__file__}'
    app.config['SESSION_DURATION'] = f'fake set in {__file__}'
    app.config['CLASSIC_COOKIE_NAME'] = f'fake set in {__file__}'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

    SessionStore.init_app(app)

    engine = create_engine('sqlite:///test.db')
    reconfigure_db(engine)
    Base(app)

    Auth(app)
    wrap(app, [AuthMiddleware])


    return app


@pytest.fixture()
def request_context(app):
    yield app.test_request_context()
