"""Testing helpers."""

from contextlib import contextmanager
from flask import Flask
from .. import util


@contextmanager
def temporary_db(database_url: str = 'sqlite:///:memory:',
                 create: bool = True, drop: bool = True):
    """Provide an in-memory sqlite database for testing purposes."""
    app = Flask('foo')
    app.config['CLASSIC_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CLASSIC_SESSION_HASH'] = 'foohash'
    with app.app_context():
        util.init_app(app)
        if create:
            util.create_all()
        try:
            with util.transaction():
                yield util.current_session()
        finally:
            if drop:
                util.drop_all()
