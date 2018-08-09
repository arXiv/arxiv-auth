from typing import Generator, Tuple, List
from datetime import datetime
from pytz import timezone
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from arxiv.base.globals import get_application_config, get_application_global

from .models import Base


@contextmanager
def transaction(commit: bool = True) -> Generator:
    """Context manager for database transaction."""
    session = current_session()
    try:
        yield session
        if commit:
            session.commit()
    except Exception as e:
        # logger.debug('Commit failed, rolling back: %s', str(e))
        session.rollback()
        raise


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('REGISTRY_DATABASE_URI', 'sqlite://')


def _get_engine(app: object = None) -> Engine:
    """Get a new :class:`.Engine` for the registry database."""
    config = get_application_config(app)
    database_uri = config.get('REGISTRY_DATABASE_URI', 'sqlite://')
    return create_engine(database_uri)


def _get_session(app: object = None) -> Session:
    """Get a new :class:`.Session` for the registry database."""
    engine = _current_engine()
    return sessionmaker(bind=engine)()


def _current_engine() -> Engine:
    """Get/create :class:`.Engine` for this context."""
    g = get_application_global()
    if not g:
        return _get_engine()
    if 'registry_data_engine' not in g:
        g.registry_data_engine = _get_engine()
    return g.registry_data_engine


def current_session() -> Session:
    """Get/create database session for this context."""
    g = get_application_global()
    if not g:
        return _get_session()
    if 'registry_data_session' not in g:
        g.registry_data_session = _get_session()
    return g.registry_data_session


def create_all() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(_current_engine())


def drop_all() -> None:
    """Drop all tables in the database."""
    Base.metadata.drop_all(_current_engine())
