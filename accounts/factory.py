"""Application factory for accounts app."""

import logging

from flask import Flask
from celery import Celery

from accounts import celeryconfig
from accounts.routes import external_api, ui
from accounts.services import baz, things
from accounts.encode import ISO8601JSONEncoder
from baseui import BaseUI

celery_app = Celery(__name__, results=celeryconfig.result_backend,
                    broker=celeryconfig.broker_url)


def create_web_app() -> Flask:
    """Initialize and configure the accounts application."""
    app = Flask('accounts')
    app.config.from_pyfile('config.py')
    app.json_encoder = ISO8601JSONEncoder

    baz.init_app(app)
    things.init_app(app)

    BaseUI(app)    # Gives us access to the base UI templates and resources.
    app.register_blueprint(external_api.blueprint)
    app.register_blueprint(ui.blueprint)

    celery_app.config_from_object(celeryconfig)
    celery_app.autodiscover_tasks(['accounts'], related_name='tasks', force=True)
    celery_app.conf.task_default_queue = 'accounts-worker'

    return app


def create_worker_app() -> Celery:
    """Initialize and configure the accounts worker application."""
    app = Flask('accounts')
    app.config.from_pyfile('config.py')

    baz.init_app(app)
    things.init_app(app)

    celery_app.config_from_object(celeryconfig)
    celery_app.autodiscover_tasks(['accounts'], related_name='tasks', force=True)
    celery_app.conf.task_default_queue = 'accounts-worker'

    return app
