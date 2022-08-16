"""Provide methods for working with user accounts."""

from typing import Optional, Generator, Tuple, Any
import hashlib
from base64 import b64encode, b64decode
from contextlib import contextmanager
from datetime import datetime
import secrets

from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm.exc import NoResultFound

from arxiv.base import logging
from .. import domain
from . import util, endorsements, exceptions, models
from .passwords import hash_password
from .exceptions import Unavailable
from .models import DBUser, DBUserPassword, DBPermanentToken, \
    DBUserNickname, DBProfile, DBPolicyClass, db


logger = logging.getLogger(__name__)


def does_username_exist(username: str) -> bool:
    """
    Determine whether a user with a particular username already exists.

    Parameters
    ----------
    username : str

    Returns
    -------
    bool

    """
    try:
        data = db.session.query(DBUserNickname) \
            .filter(DBUserNickname.nickname == username) \
            .first()
    except OperationalError as e:
        raise Unavailable('Database is temporarily unavailable') from e
    if data:
        return True
    return False


def does_email_exist(email: str) -> bool:
    """
    Determine whether a user with a particular address already exists.

    Parameters
    ----------
    email : str

    Returns
    -------
    bool

    """
    try:
        data = db.session.query(DBUser).filter(DBUser.email == email).first()
    except OperationalError as e:
        raise Unavailable('Database is temporarily unavailable') from e
    if data:
        return True
    return False


def register(user: domain.User, password: str, ip: str,
             remote_host: str) -> Tuple[domain.User, domain.Authorizations]:
    """
    Create a new user.

    Parameters
    ----------
    user : :class:`.domain.User`
        User data for the new account.
    password : str
        Password for the account.
    ip : str
        The IP address of the client requesting the registration.
    remote_host : str
        The remote hostname of the client requesting the registration.

    Returns
    -------
    :class:`.domain.User`
        Data about the created user.
    :class:`.domain.Authorizations`
        Privileges attached to the created user.

    """
    try:
        db_user, db_nick, db_profile = _create(user, password, ip, remote_host)
        db.session.commit()
    except OperationalError as e:
        raise Unavailable('Database is temporarily unavailable') from e
    except Exception as e:
        logger.debug(e)
        raise exceptions.RegistrationFailed('Could not create user')# from e

    user = domain.User(
        user_id=str(db_user.user_id),
        username=db_nick.nickname,
        email=db_user.email,
        name=domain.UserFullName(
            forename=db_user.first_name,
            surname=db_user.last_name,
            suffix=db_user.suffix_name
        ),
        profile=db_profile.to_domain() if db_profile is not None else None
    )
    auths = domain.Authorizations(
        classic=util.compute_capabilities(db_user),
        scopes=util.get_scopes(db_user),
        endorsements=endorsements.get_endorsements(user)
    )
    return user, auths


def get_user_by_id(user_id: str) -> domain.User:
    """Load user data from the database."""
    try:
        db_user, db_nick, db_profile = _get_user_data(user_id)
    except OperationalError as e:
        raise Unavailable('Database is temporarily unavailable') from e
    user = domain.User(
        user_id=str(db_user.user_id),
        username=db_nick.nickname,
        email=db_user.email,
        name=domain.UserFullName(
            forename=db_user.first_name,
            surname=db_user.last_name,
            suffix=db_user.suffix_name
        ),
        profile=db_profile.to_domain() if db_profile is not None else None
    )
    return user


def update(user: domain.User) -> Tuple[domain.User, domain.Authorizations]:
    """Update a user in the database."""
    if user.user_id is None:
        raise ValueError('User ID must be set')

    db_user, db_nick, db_profile = _get_user_data(user.user_id)
    # TODO: we probably want to think a bit more about changing usernames
    # and e-mail addresses.
    #
    # _update_field_if_changed(db_nick, 'nickname', user.username)
    # _update_field_if_changed(db_user, 'email', user.email)
    if user.name is not None:
        _update_field_if_changed(db_user, 'first_name', user.name.forename)
        _update_field_if_changed(db_user, 'last_name', user.name.surname)
        _update_field_if_changed(db_user, 'suffix_name', user.name.suffix)
    if user.profile is not None:
        if db_profile is not None:
            def _has_group(group: str) -> int:
                if user.profile is None:
                    return 0
                return int(group in user.profile.submission_groups)

            _update_field_if_changed(db_profile, 'affiliation',
                                     user.profile.affiliation)
            _update_field_if_changed(db_profile, 'country',
                                     user.profile.country)
            _update_field_if_changed(db_profile, 'rank', user.profile.rank)
            _update_field_if_changed(db_profile, 'url',
                                     user.profile.homepage_url)
            _update_field_if_changed(db_profile, 'archive',
                                     user.profile.default_archive)
            _update_field_if_changed(db_profile, 'subject_class',
                                     user.profile.default_subject)
            for grp, field in DBProfile.GROUP_FLAGS:
                _update_field_if_changed(db_profile, field,
                                         _has_group(grp))
            db.session.add(db_profile)
        else:
            db_profile = _create_profile(user, db_user)

    db.session.add(db_nick)
    db.session.add(db_user)
    db.session.commit()

    user = domain.User(
        user_id=str(db_user.user_id),
        username=db_nick.nickname,
        email=db_user.email,
        name=domain.UserFullName(
            forename=db_user.first_name,
            surname=db_user.last_name,
            suffix=db_user.suffix_name
        ),
        profile=db_profile.to_domain() if db_profile is not None else None
    )
    auths = domain.Authorizations(
        classic=util.compute_capabilities(db_user),
        scopes=util.get_scopes(db_user),
        endorsements=endorsements.get_endorsements(user)
    )
    return user, auths


def _update_field_if_changed(obj: Any, field: Any, update_with: Any) -> None:
    if getattr(obj, field) != update_with:
        setattr(obj, field, update_with)


def _get_user_data(user_id: str) -> Tuple[DBUser, DBUserNickname, DBProfile]:

    try:
        db_user, db_nick = db.session.query(DBUser, DBUserNickname) \
            .filter(DBUser.user_id == user_id) \
            .filter(DBUser.flag_approved == 1) \
            .filter(DBUser.flag_deleted == 0) \
            .filter(DBUser.flag_banned == 0) \
            .filter(DBUserNickname.flag_primary == 1) \
            .filter(DBUserNickname.flag_valid == 1) \
            .filter(DBUserNickname.user_id == DBUser.user_id) \
            .first()
    except TypeError:   # first() returns a single None if no match.
        raise exceptions.NoSuchUser('User does not exist')
    # Profile may not exist.
    db_profile = db.session.query(models.DBProfile) \
        .filter(models.DBProfile.user_id == user_id) \
        .first()
    if not db_user:
        raise exceptions.NoSuchUser('User does not exist')
    return db_user, db_nick, db_profile


def _create_profile(user: domain.User, db_user: DBUser) -> DBProfile:
    def _has_group(group: str) -> int:
        if user.profile is None:
            return 0
        return int(group in user.profile.submission_groups)

    db_profile = DBProfile(
        user=db_user,
        country=user.profile.country if user.profile else None,
        affiliation=user.profile.affiliation if user.profile else None,
        url=user.profile.homepage_url if user.profile else None,
        rank=user.profile.rank if user.profile else None,
        archive=user.profile.default_archive if user.profile else None,
        subject_class=user.profile.default_subject if user.profile else None,
        original_subject_classes='',
        flag_group_physics=_has_group('grp_physics'),
        flag_group_math=_has_group('grp_math'),
        flag_group_cs=_has_group('grp_cs'),
        flag_group_q_bio=_has_group('grp_q-bio'),
        flag_group_q_fin=_has_group('grp_q-fin'),
        flag_group_stat=_has_group('grp_stat'),
        flag_group_eess=_has_group('grp_eess'),
        flag_group_econ=_has_group('grp_econ'),
    )
    db.session.add(db_profile)
    return db_profile


def _create(user: domain.User, password: str, ip: str, remote_host: str) \
        -> Tuple[DBUser, DBUserNickname, Optional[DBProfile]]:
    if not user.name.forename:
        raise ValueError("Must have forename to create user")
    if not user.name.surname:
        raise ValueError("Must have surname to create user")

    data = dict(
        email=user.email,
        policy_class=DBPolicyClass.PUBLIC_USER,
        joined_ip_num=ip,
        joined_remote_host=remote_host,
        joined_date=util.now(),
        tracking_cookie=''      # TODO: set this.
    )
    if user.name is not None:
        data.update(dict(
            first_name=user.name.forename,
            last_name=user.name.surname,
            suffix_name=user.name.suffix
        ))

    # Main user entry.
    db_user = DBUser(**data)
    db.session.add(db_user)

    # Nickname is where we keep the username.
    db_nick = DBUserNickname(
        user=db_user,
        nickname=user.username,
        flag_valid=1,
        flag_primary=1
    )
    db.session.add(db_nick)

    db_profile: Optional[DBProfile]
    if user.profile is not None:
        db_profile = _create_profile(user, db_user)
    else:
        db_profile = None

    db_pass = DBUserPassword(
        user=db_user,
        password_enc=hash_password(password)
    )
    db.session.add(db_pass)
    return db_user, db_nick, db_profile
