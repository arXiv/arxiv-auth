"""Testing helpers."""
from contextlib import contextmanager

from flask import Flask
from sqlalchemy import create_engine

from arxiv.db.models import reconfigure_db
from .. import util


@contextmanager
def temporary_db(db_uri: str, create: bool = True, drop: bool = True):
    """Provide an in-memory sqlite database for testing purposes."""
    app = Flask('foo')
    app.config['CLASSIC_SESSION_HASH'] = 'foohash'
    app.config['SESSION_DURATION'] = 3600
    app.config['CLASSIC_COOKIE_NAME'] = 'tapir_session'

    engine = create_engine(db_uri)
    reconfigure_db (engine)

    with app.app_context():
        if create:
            util.create_all()
        try:
            with util.transaction():
                yield util.session
        finally:
            if drop:
                util.drop_all()
