import pytest

from flask import Flask
from arxiv_auth import legacy

from arxiv_auth.auth.sessions import SessionStore
from arxiv_auth.legacy.util import init_app as legacy_init_app
from arxiv_auth.legacy.util import create_all as legacy_create_all
from arxiv_auth import auth, factory
from arxiv_auth.auth.middleware import AuthMiddleware


@pytest.fixture()
def app():
    return factory.create_web_app()

@pytest.fixture()
def request_context(app):
    yield app.test_request_context()
