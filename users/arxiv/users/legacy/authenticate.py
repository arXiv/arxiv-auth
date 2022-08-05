"""Provide an API for user authentication using the legacy database."""

from typing import Optional, Generator, Tuple
import hashlib
from base64 import b64encode, b64decode
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm.exc import NoResultFound

from . import util, endorsements
from .. import domain
from ..auth import scopes
from arxiv.base import logging

from .models import DBUser, DBUserPassword, DBPermanentToken, \
    DBUserNickname, DBProfile, db
from .exceptions import NoSuchUser, AuthenticationFailed, \
    PasswordAuthenticationFailed, Unavailable

logger = logging.getLogger(__name__)

PassData = Tuple[DBUser, DBUserPassword, DBUserNickname, DBProfile]
TokenData = Tuple[DBUser, DBPermanentToken, DBUserNickname, DBProfile]


def authenticate(username_or_email: Optional[str] = None,
                 password: Optional[str] = None, token: Optional[str] = None) \
        -> Tuple[domain.User, domain.Authorizations]:
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
    :class:`domain.User`
    :class:`domain.Authorizations`

    Raises
    ------
    :class:`AuthenticationFailed`
        Failed to authenticate user with provided credentials.
    :class:`Unavailable`
        Unable to connect to DB.
    """
    try:
        # Users may log in using either their username or their email address.
        if username_or_email and password:
            db_user, _, db_nick, db_profile \
                = _authenticate_password(username_or_email, password)
        # The "tapir permanent token" is effectively a bearer token. If passed,
        # a new session will be "automatically" created (from the user's
        # perspective).
        elif token:
            db_user, _, db_nick, db_profile = _authenticate_token(token)

        else:
            logger.debug('Neither username/password nor token provided')
            raise AuthenticationFailed('Username+password or token required')
    except OperationalError as e:
        raise Unavailable('Database is temporarily unavailable') from e
    except Exception as ex:
        raise AuthenticationFailed() from ex
    logger.debug('authenticate: got profile %s', db_profile)
    user = domain.User(
        user_id=str(db_user.user_id),
        username=db_nick.nickname,
        email=db_user.email,
        name=domain.UserFullName(
            forename=db_user.first_name,
            surname=db_user.last_name,
            suffix=db_user.suffix_name
        ),
        profile=db_profile.to_domain() if db_profile else None,
        verified=bool(db_user.flag_email_verified)
    )
    auths = domain.Authorizations(
        classic=util.compute_capabilities(db_user),
        scopes=util.get_scopes(db_user),
        endorsements=endorsements.get_endorsements(user)
    )
    return user, auths


def _authenticate_token(token: str) -> TokenData:
    """
    Authenticate using a permanent token.

    Parameters
    ----------
    token : str

    Returns
    -------
    :class:`.DBUser`
    :class:`.DBPermanentToken`
    :class:`.DBUserNickname`
    :class:`.DBProfile`

    Raises
    ------
    :class:`AuthenticationFailed`
        Raised if the token is malformed, or there is no corresponding token
        in the database.

    """
    try:
        user_id, secret = token.split('-')
    except ValueError as e:
        raise AuthenticationFailed('Token is malformed') from e
    try:
        return _get_token(user_id, secret)
    except NoSuchUser as e:
        logger.debug('Not a valid permanent token')
        raise AuthenticationFailed('Invalid token') from e


def _authenticate_password(username_or_email: str, password: str) -> PassData:
    """
    Authenticate using username/email and password.

    Parameters
    ----------
    username_or_email : str
        Either the email address or username of the authenticating user.
    password : str

    Returns
    -------
    :class:`.DBUser`
    :class:`.DBUserPassword`
    :class:`.DBUserNickname`

    Raises
    ------
    :class:`AuthenticationFailed`
        Raised if the user does not exist or the password is incorrect.
    :class:`RuntimeError`
        Raised when other problems arise.

    """
    logger.debug(f'Authenticate with password, user: {username_or_email}')

    if not password:
        raise RuntimeError('Passed empty password')
    if not isinstance(password, str):
        raise RuntimeError('Passed non-str password: {type(password)}')
    if not util.is_ascii(password):
        raise RuntimeError('Password non-ascii password')

    if not username_or_email:
        raise RuntimeError('Passed empty username_or_email')
    if not isinstance(password, str):
        raise RuntimeError('Passed non-str username_or_email: {type(username_or_email)}')
    if len(username_or_email) > 255:
        raise RuntimeError(f'Passed username_or_email too long: len {len(username_or_email)}')
    if not util.is_ascii(username_or_email):
        raise RuntimeError('Passed non-ascii username_or_email')

    try:
        db_user, db_pass, db_nick, db_profile \
            = _get_user_by_username(username_or_email)
        logger.debug('profile: %s', db_profile)
    except NoSuchUser as e:
        logger.debug(f'No such user: {username_or_email}')
        raise AuthenticationFailed('Invalid username or password') from e
    logger.debug(f'Got user with user_id: {db_user.user_id}')
    try:
        util.check_password(password, db_pass.password_enc)
    except PasswordAuthenticationFailed as e:
        raise AuthenticationFailed('Invalid username or password') from e
    return db_user, db_pass, db_nick, db_profile


def _get_user_by_username(username_or_email: str) -> PassData:
    """
    Retrieve user data by username or email address.

    Parameters
    ----------
    username_or_email : str

    Returns
    -------
    :class:`.DBUser`
    :class:`.DBUserPassword`
    :class:`.DBUserNickname`
    :class:`.DBProfile`

    Raises
    ------
    :class:`NoSuchUser`
        Raised when the user cannot be found.
    :class:`RuntimeError`
        Raised when other problems arise.

    """
    tapir_user: DBUser = db.session.query(DBUser) \
        .filter(DBUser.email == username_or_email) \
        .filter(DBUser.flag_approved == 1) \
        .filter(DBUser.flag_deleted == 0) \
        .filter(DBUser.flag_banned == 0) \
        .first()
    if tapir_user:
        tapir_nick: DBUserNickname = db.session.query(DBUserNickname) \
            .filter(DBUserNickname.user_id == tapir_user.user_id) \
            .filter(DBUserNickname.flag_primary == 1) \
            .first()
    else:   # Usernames are stored in a separate table
        tapir_nick = db.session.query(DBUserNickname) \
            .filter(DBUserNickname.nickname == username_or_email) \
            .filter(DBUserNickname.flag_valid == 1) \
            .first()
        if tapir_nick:
            tapir_user = db.session.query(DBUser) \
                .filter(DBUser.user_id == tapir_nick.user_id) \
                .filter(DBUser.flag_approved == 1) \
                .filter(DBUser.flag_deleted == 0) \
                .filter(DBUser.flag_banned == 0) \
                .first()

    if not tapir_user:
        raise NoSuchUser('User does not exist')
    tapir_password: DBUserPassword = db.session.query(DBUserPassword) \
        .filter(DBUserPassword.user_id == tapir_user.user_id) \
        .first()
    if not tapir_password:
        raise RuntimeError(f'Missing password for {username_or_email}')
    tapir_profile: DBProfile = db.session.query(DBProfile) \
        .filter(DBProfile.user_id == tapir_user.user_id) \
        .first()
    return tapir_user, tapir_password, tapir_nick, tapir_profile


def _invalidate_token(user_id: str, secret: str) -> None:
    """
    Invalidate a user's permanent login token.

    Parameters
    ----------
    user_id : str
    secret : str

    Raises
    ------
    :class:`NoSuchUser`
        Raised when the token or user cannot be found.

    """
    _, db_token, _, _ = _get_token(user_id, secret)
    db_token.valid = 0
    db.session.add(db_token)
    db.session.commit()


def _get_token(user_id: str, secret: str, valid: int = 1) -> TokenData:
    """
    Retrieve a user's permanent token.

    User ID and token are used together as the primary key for the token.

    Parameters
    ----------
    user_id : str
    secret : str
    valid : int
        (default: 1)

    Returns
    -------
    :class:`.DBUser`
    :class:`.DBPermanentToken`
    :class:`.DBUserNickname`
    :class:`.DBProfile`

    Raises
    ------
    :class:`NoSuchUser`
        Raised when the token or user cannot be found.

    """
    db_token: DBPermanentToken = db.session.query(DBPermanentToken) \
        .filter(DBPermanentToken.user_id == user_id) \
        .filter(DBPermanentToken.secret == secret) \
        .filter(DBPermanentToken.valid == valid) \
        .first()    # The token must still be valid.
    if not db_token:
        raise NoSuchUser('No such token')
    if db_token:
        db_user: DBUser = db.session.query(DBUser) \
            .filter(DBUser.user_id == user_id) \
            .first()
    if not db_user:
        raise NoSuchUser('No user with passed token exists')
    db_nick: DBUserNickname = db.session.query(DBUserNickname) \
        .filter(DBUserNickname.user_id == db_user.user_id) \
        .filter(DBUserNickname.flag_primary == 1) \
        .first()
    tapir_profile: DBProfile = db.session.query(DBProfile) \
        .filter(DBProfile.user_id == db_user.user_id) \
        .first()
    return db_user, db_token, db_nick, tapir_profile
