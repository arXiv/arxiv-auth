"""Testing helpers."""

import os
from contextlib import contextmanager
from flask import Flask
from .. import util


@contextmanager
def temporary_db(create: bool = True, drop: bool = True):
    """Provide an in-memory sqlite database for testing purposes."""
    app = Flask('foo')
    app.config['CLASSIC_DATABASE_URI'] = os.environ.get('CLASSIC_DATABASE_URI')
    app.config['CLASSIC_SESSION_HASH'] = 'foohash'
    app.config['SESSION_DURATION'] = 3600
    app.config['CLASSIC_COOKIE_NAME'] = 'tapir_session'

    with app.app_context():
        if create:
            util.create_all()
        try:
            with util.transaction():
                yield util.session
        finally:
            if drop:
                util.drop_all()
