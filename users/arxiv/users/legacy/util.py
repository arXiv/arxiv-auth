"""Helpers and Flask application integration."""

from typing import Generator, Tuple, List
from datetime import datetime
from contextlib import contextmanager
import secrets
from base64 import b64encode, b64decode
import hashlib
from collections import Counter

from flask import current_app

from sqlalchemy.engine import Engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from arxiv.base.globals import get_application_config, get_application_global

from ..auth import scopes
from .. import domain
from .models import Base, DBUser, DBPolicyClass, DBEndorsement, DBSession
from .exceptions import SessionUnknown, PasswordAuthenticationFailed

# TODO: timezone!


def now() -> int:
    """Get the current epoch/unix time."""
    return epoch(datetime.now())


def epoch(t: datetime) -> int:
    """Convert a :class:`.datetime` to UNIX time."""
    return int(round((t - datetime.utcfromtimestamp(0)).total_seconds()))


def from_epoch(t: int) -> datetime:
    """Get a :class:`datetime` from an UNIX timestamp."""
    return datetime.utcfromtimestamp(t)


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


def unpack_cookie(session_cookie: str) -> Tuple[str, str, str, int, str]:
    """Unpack the legacy session cookie."""
    parts = session_cookie.split(':')
    payload = tuple(part for part in parts[:-1])
    try:
        expected_cookie = pack_cookie(*payload)
        assert expected_cookie == session_cookie
    except (TypeError, AssertionError) as e:
        raise SessionUnknown('Invalid session cookie; forged?') from e
    return payload


def pack_cookie(session_id: str, user_id: str, ip: str, capabilities: int) \
        -> bytes:
    """
    Generate a value for the classic session cookie.

    Parameters
    ----------
    session_id : str
    user_id : str
    ip : str
        Client IP address.
    capabilities : str
        This is essentially a user privilege level.

    Returns
    -------
    bytes
        Signed cookie value.

    """
    session_hash = get_application_config()['CLASSIC_SESSION_HASH']
    value = ':'.join(map(str, [session_id, user_id, ip, capabilities]))
    to_sign = f'{value}-{session_hash}'.encode('utf-8')
    cookie_hash = b64encode(hashlib.sha256(to_sign).digest())
    return value + ':' + cookie_hash.decode('utf-8')


def compute_capabilities(tapir_user: DBUser) -> int:
    """Calculate the privilege level code for a user."""
    return int(sum([2 * tapir_user.flag_edit_users,
                    4 * tapir_user.flag_email_verified,
                    8 * tapir_user.flag_edit_system]))


def get_scopes(db_user: DBUser) -> List[str]:
    """Generate a list of authz scopes for a legacy user based on class."""
    if db_user.policy_class == DBPolicyClass.PUBLIC_USER:
        return scopes.AUTHENTICATED_USER
    return []


def get_endorsements(db_user: DBUser) -> List[domain.Category]:
    """Load endorsed categories for a user."""
    with transaction() as session:
        data: List[Row] = (
            session.query(DBEndorsement)
            .filter(DBEndorsement.endorsee_id == db_user.user_id)
            .all()
        )
    return aggregate_endorsements(data)


def aggregate_endorsements(data: List[DBEndorsement]) -> List[domain.Category]:
    """Generate a set of endorsed categories from legacy endorsement data."""
    endorsement_points = Counter()
    for db_endorsement in data:
        category = (db_endorsement.archive, db_endorsement.subject_class)
        # This should be robust to negative endorsements.
        endorsement_points[category] += db_endorsement.point_value
    return [domain.Category(archive=archive, subject=subject)
            for (archive, subject), points
            in endorsement_points.items() if points > 0]
