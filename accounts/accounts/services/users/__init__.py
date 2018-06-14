"""Integration with the users datastore. Provides authentication."""
from typing import Optional, Generator, Tuple
import hashlib
from base64 import b64encode, b64decode
from contextlib import contextmanager
from datetime import datetime
import secrets

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from arxiv.base.globals import get_application_config, get_application_global
from arxiv.base import logging

from accounts.domain import User, UserPrivileges, UserRegistration

from .models import Base, TapirUser, TapirUserPassword, TapirPermanentToken, \
    TapirUserNickname, Profile


logger = logging.getLogger(__name__)


class AuthenticationFailed(RuntimeError):
    """Failed to authenticate user with provided credentials."""


class NoSuchUser(RuntimeError):
    """User does not exist."""


class PasswordAuthenticationFailed(RuntimeError):
    """Password is not correct."""


@contextmanager
def transaction() -> Generator:
    """Context manager for database transaction."""
    session = _current_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        # logger.debug('Commit failed, rolling back: %s', str(e))
        session.rollback()
        raise


def register(user_registration: UserRegistration,
             ip_address: str, remote_host: str) -> User:
    """Add a new user to the database."""
    with transaction() as session:
        # Main user entry.
        db_user = TapirUser(
            first_name=user_registration.name.forename,
            last_name=user_registration.name.surname,
            suffix_name=user_registration.name.suffix,
            email=user_registration.email,
            joined_ip_num=ip_address,
            joined_remote_host=remote_host,
            joined_date=_now(),
            tracking_cookie='',  # TODO: how to set?
        )
        session.add(db_user)

        # Nickname is (apparently) where we keep the username.
        db_nick = TapirUserNickname(
            user=db_user,
            nickname=user_registration.username,
            flag_valid=1,
            flag_primary=1
        )
        session.add(db_nick)

        def _has_group(group: str) -> int:
            return int(group in user_registration.profile.submission_groups)

        # TODO: where to put the new categories?
        db_profile = Profile(
            user=db_user,
            country=user_registration.profile.country,
            affiliation=user_registration.profile.affiliation,
            url=user_registration.profile.homepage_url,
            rank=user_registration.profile.rank,
            archive=user_registration.profile.default_archive,
            subject_class=user_registration.profile.default_subject,
            flag_group_physics=_has_group('grp_physics'),
            flag_group_math=_has_group('grp_math'),
            flag_group_cs=_has_group('grp_cs'),
            flag_group_q_bio=_has_group('grp_q-bio'),
            flag_group_q_fin=_has_group('grp_q-fin'),
            flag_group_stat=_has_group('grp_stat'),
        )
        session.add(db_profile)

        db_pass = TapirUserPassword(
            user=db_user,
            password_enc=_hash_password
        )
        session.add(db_pass)
        session.commit()


def authenticate(username_or_email: Optional[str]=None,
                 password: Optional[str]=None,
                 token: Optional[str]=None) -> User:
    """
    Validate username/password. If successful, retrieve user details.

    Parameters
    ----------
    username_or_email : str
        Users may log in with either their username or their email address.
    password : str
        Password (as entered). Danger, Will Robinson!
    token : str
        Alternatively, the user may provide a bearer token. This is currently
        used to support "permanent" sessions, in which the token is used to
        "automatically" log the user in (i.e. without entering credentials).

    Returns
    -------
    :class:`.User`

    Raises
    ------
    :class:`AuthenticationFailed`
        Failed to authenticate user with provided credentials.

    """
    # Users may log in using either their username or their email address.
    if username_or_email and password:
        logger.debug(f'Authenticate with password, user: {username_or_email}')
        try:
            db_user, db_password, db_nick = _get_user(username_or_email)
        except NoSuchUser as e:
            logger.debug(f'No such user: {username_or_email}')
            raise AuthenticationFailed('Invalid username or password') from e
        logger.debug(f'Got user with user_id: {db_user.user_id}')
        try:
            _check_password(password, db_password.password_enc)
        except PasswordAuthenticationFailed as e:
            raise AuthenticationFailed('Invalid username or password') from e
    # The "tapir permanent token" is effectively a bearer token. If passed,
    # a new session will be "automatically" created (from the user's
    # perspective).
    elif token:
        try:
            user_id, secret = token.split('-')
        except ValueError:
            raise AuthenticationFailed('Token is malformed')
        try:
            db_user, db_token, db_nick = _get_token(user_id, secret)
            logger.debug(f'Got user with user_id: {db_user.user_id}')
        except NoSuchUser as e:
            logger.debug('Not a valid permanent token')
            raise AuthenticationFailed('Invalid token') from e
    else:
        logger.debug('Neither username/password nor token provided')
        raise AuthenticationFailed('Username+password or token required')
    return User(
        user_id=db_user.user_id,
        username=db_nick.nickname,
        email=db_user.email,
        privileges=UserPrivileges(
            classic=_compute_capabilities(db_user)
        )
    )


def _compute_capabilities(tapir_user: TapirUser) -> int:
    """Calculate the privilege level code for a user."""
    return int(sum([2 * tapir_user.flag_edit_users,
                    4 * tapir_user.flag_email_verified,
                    8 * tapir_user.flag_edit_system]))


# TODO: encrypted should be str; just encode('ascii') before b64decode.
def _check_password(password: str, encrypted: bytes) -> None:
    decoded = b64decode(encrypted)
    salt = decoded[:4]
    enc_hashed = decoded[4:]
    pass_hashed = hashlib.sha1(salt + b'-' + password.encode('utf-8')).digest()
    if pass_hashed != enc_hashed:
        raise PasswordAuthenticationFailed('Incorrect password')


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(4)
    hashed = hashlib.sha1(salt + b'-' + password.encode('utf-8')).digest()
    return b64encode(salt + hashed).decode('ascii')


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
    if 'classic_engine' not in g:
        g.classic_engine = _get_engine()
    return g.classic_engine


def _current_session() -> Session:
    """Get/create database session for this context."""
    g = get_application_global()
    if not g:
        return _get_session()
    if 'classic_session_store' not in g:
        g.classic_session_store = _get_session()
    return g.classic_session_store


def create_all() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(_current_engine())


def drop_all() -> None:
    """Drop all tables in the database."""
    Base.metadata.drop_all(_current_engine())


# TODO: look at if/how we can optimize these queries.
def _get_user(username_or_email: str) \
        -> Tuple[TapirUser, TapirUserPassword, TapirUserNickname]:
    with transaction() as session:
        tapir_user: TapirUser = session.query(TapirUser) \
            .filter(TapirUser.email == username_or_email) \
            .filter(TapirUser.flag_approved == 1) \
            .filter(TapirUser.flag_deleted == 0) \
            .filter(TapirUser.flag_banned == 0) \
            .first()
        if tapir_user:
            tapir_nick: TapirUserNickname = session.query(TapirUserNickname) \
                .filter(TapirUserNickname.user_id == tapir_user.user_id) \
                .filter(TapirUserNickname.flag_primary == 1) \
                .first()
        else:   # Usernames are stored in a separate table (!).
            tapir_nick = session.query(TapirUserNickname) \
                .filter(TapirUserNickname.nickname == username_or_email) \
                .filter(TapirUserNickname.flag_valid == 1) \
                .first()
            if tapir_nick:
                tapir_user = session.query(TapirUser) \
                    .filter(TapirUser.user_id == tapir_nick.user_id) \
                    .filter(TapirUser.flag_approved == 1) \
                    .filter(TapirUser.flag_deleted == 0) \
                    .filter(TapirUser.flag_banned == 0) \
                    .first()
        if not tapir_user:
            raise NoSuchUser('User does not exist')
        tapir_password: TapirUserPassword = session.query(TapirUserPassword) \
            .filter(TapirUserPassword.user_id == tapir_user.user_id) \
            .first()
        if not tapir_password:
            raise RuntimeError(f'Missing password for {username_or_email}')
    return tapir_user, tapir_password, tapir_nick


def _get_token(user_id: str, secret: str) \
        -> Tuple[TapirUser, TapirPermanentToken, TapirUserNickname]:
    # User ID and token are used together as a primary key.
    with transaction() as session:
        db_token: TapirPermanentToken = session.query(TapirPermanentToken) \
            .filter(TapirPermanentToken.user_id == user_id) \
            .filter(TapirPermanentToken.secret == secret) \
            .filter(TapirPermanentToken.valid == 1) \
            .first()    # The token must still be valid.
        if not db_token:
            raise NoSuchUser('No such token')
        if db_token:
            db_user: TapirUser = session.query(TapirUser) \
                .filter(TapirUser.user_id == user_id) \
                .first()
        if not db_user:
            raise NoSuchUser('No user with passed token exists')
        db_nick: TapirUserNickname = session.query(TapirUserNickname) \
            .filter(TapirUserNickname.user_id == db_user.user_id) \
            .filter(TapirUserNickname.flag_primary == 1) \
            .first()
    return db_user, db_token, db_nick


def _now() -> int:
    epoch = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
    return int(round(epoch))
