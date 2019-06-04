"""Helpers and Flask application integration."""

from typing import Generator, Tuple, List, Optional, Any
from datetime import datetime
from pytz import timezone, UTC
from contextlib import contextmanager
import secrets
from base64 import b64encode, b64decode
import hashlib
from collections import Counter

from werkzeug.local import LocalProxy
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from arxiv.base import logging
from arxiv.base.globals import get_application_config, get_application_global

from ..auth import scopes
from .. import domain
from .models import db, DBUser, DBPolicyClass, DBEndorsement, DBSession
from .exceptions import UnknownSession, PasswordAuthenticationFailed

EASTERN = timezone('US/Eastern')
logger = logging.getLogger(__name__)
logger.propagate = False


def now() -> int:
    """Get the current epoch/unix time."""
    return epoch(datetime.now(tz=UTC))


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
    try:
        yield db.session
        # The caller may have explicitly committed already, in order to
        # implement exception handling logic. We only want to commit here if
        # there is anything remaining that is not flushed.
        if db.session.new or db.session.dirty or db.session.deleted:
            db.session.commit()
    except Exception as e:
        logger.error('Commit failed, rolling back: %s', str(e))
        db.session.rollback()
        raise


def init_app(app: Optional[LocalProxy]) -> None:
    """Set configuration defaults and attach session to the application."""
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
    if db_user.policy_class == DBPolicyClass.ADMIN:
        return scopes.ADMIN_USER
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
    timeout: str = config['SESSION_DURATION']
    return int(timeout)


def is_available(**kwargs: Any) -> bool:
    """Check our connection to the database."""
    try:
        db.session.query("1").from_statement(text("SELECT 1")).all()
    except Exception as e:
        logger.error('Encountered an error talking to database: %s', e)
        return False
    return True
