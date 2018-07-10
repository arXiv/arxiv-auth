"""Helpers and Flask application integration."""

from typing import Generator, Tuple, List
from datetime import datetime
from pytz import timezone
from contextlib import contextmanager
import secrets
from base64 import b64encode, b64decode
import hashlib
from collections import Counter

from sqlalchemy.engine import Engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from arxiv.base.globals import get_application_config, get_application_global

from ..auth import scopes
from .. import domain
from .models import Base, DBUser, DBPolicyClass, DBEndorsement, DBSession
from .exceptions import UnknownSession, PasswordAuthenticationFailed

EASTERN = timezone('US/Eastern')


def now() -> int:
    """Get the current epoch/unix time."""
    return epoch(datetime.now(tz=EASTERN))


def epoch(t: datetime) -> int:
    """Convert a :class:`.datetime` to UNIX time."""
    delta = t - datetime.fromtimestamp(0, tz=EASTERN)
    return int(round((delta).total_seconds()))


def from_epoch(t: int) -> datetime:
    """Get a :class:`datetime` from an UNIX timestamp."""
    return datetime.fromtimestamp(t, tz=EASTERN)


@contextmanager
def transaction() -> Generator:
    """Context manager for database transaction."""
    session = current_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        # logger.debug('Commit failed, rolling back: %s', str(e))
        session.rollback()
        raise


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('CLASSIC_DATABASE_URI', 'sqlite://')


def _get_engine(app: object = None) -> Engine:
    """Get a new :class:`.Engine` for the classic database."""
    config = get_application_config(app)
    database_uri = config.get('CLASSIC_DATABASE_URI', 'sqlite://')
    return create_engine(database_uri)


def _get_session(app: object = None) -> Session:
    """Get a new :class:`.Session` for the classic database."""
    engine = _current_engine()
    return sessionmaker(bind=engine)()


def _current_engine() -> Engine:
    """Get/create :class:`.Engine` for this context."""
    g = get_application_global()
    if not g:
        return _get_engine()
    if 'user_data_engine' not in g:
        g.user_data_engine = _get_engine()
    return g.user_data_engine


def current_session() -> Session:
    """Get/create database session for this context."""
    g = get_application_global()
    if not g:
        return _get_session()
    if 'user_data' not in g:
        g.user_data = _get_session()
    return g.user_data


def create_all() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(_current_engine())


def drop_all() -> None:
    """Drop all tables in the database."""
    Base.metadata.drop_all(_current_engine())


def hash_password(password: str) -> str:
    """Generate a secure hash of a password."""
    salt = secrets.token_bytes(4)
    hashed = hashlib.sha1(salt + b'-' + password.encode('utf-8')).digest()
    return b64encode(salt + hashed).decode('ascii')


def check_password(password: str, encrypted: bytes) -> None:
    """Check a password against an encrypted hash."""
    decoded = b64decode(encrypted)
    salt = decoded[:4]
    enc_hashed = decoded[4:]
    pass_hashed = hashlib.sha1(salt + b'-' + password.encode('utf-8')).digest()
    if pass_hashed != enc_hashed:
        raise PasswordAuthenticationFailed('Incorrect password')


def compute_capabilities(tapir_user: DBUser) -> int:
    """Calculate the privilege level code for a user."""
    return int(sum([2 * tapir_user.flag_edit_users,
                    4 * tapir_user.flag_email_verified,
                    8 * tapir_user.flag_edit_system]))


def get_scopes(db_user: DBUser) -> List[str]:
    """Generate a list of authz scopes for a legacy user based on class."""
    if db_user.policy_class == DBPolicyClass.PUBLIC_USER:
        return scopes.GENERAL_USER
    return []


def is_configured() -> bool:
    """Determine whether or not the legacy database is configured."""
    config = get_application_config()
    if 'CLASSIC_DATABASE_URI' in config and 'CLASSIC_SESSION_HASH' in config:
        return True
    return False


def get_session_hash() -> str:
    """Get the legacy hash secret."""
    config = get_application_config()
    session_hash: str = config['CLASSIC_SESSION_HASH']
    return session_hash


def get_session_duration() -> int:
    """Get the session duration from the config."""
    config = get_application_config()
    timeout: str = config['CLASSIC_SESSION_TIMEOUT']
    return int(timeout)
