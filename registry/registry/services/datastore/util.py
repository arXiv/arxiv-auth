from typing import Generator, Tuple, List
from datetime import datetime
from pytz import timezone, UTC
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from arxiv.base.globals import get_application_config, get_application_global

from arxiv.db import session, transaction, engine, Base
from .models import db


def create_all() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(engine)


def drop_all() -> None:
    """Drop all tables in the database."""
    Base.metadata.drop_all(engine)
