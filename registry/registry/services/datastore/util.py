from typing import Generator, Tuple, List
from datetime import datetime
from pytz import timezone, UTC
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from arxiv.base.globals import get_application_config, get_application_global

from .models import db


@contextmanager
def transaction(commit: bool = True) -> Generator:
    """Context manager for database transaction."""
    try:
        yield db.session
        if commit:
            db.session.commit()
    except Exception as e:
        # logger.debug('Commit failed, rolling back: %s', str(e))
        db.session.rollback()
        raise


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    db.init_app(app)


def current_session() -> Session:
    """Get/create database session for this context."""
    return db.session


def create_all() -> None:
    """Create all tables in the database."""
    db.create_all()


def drop_all() -> None:
    """Drop all tables in the database."""
    db.drop_all()
