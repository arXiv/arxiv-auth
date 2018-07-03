"""Provides API for registering legacy users."""

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

from .. import domain
from arxiv.base import logging

from .models import DBUser, DBUserPassword, DBPermanentToken, \
    DBUserNickname, DBProfile, DBPolicyClass

from .util import now, transaction, hash_password, compute_capabilities, \
    get_scopes
from .endorsements import get_endorsements


def username_exists(username: str) -> bool:
    """Determine whether or not a username already exists in the DB."""
    with transaction() as session:
        data = (
            session.query(DBUserNickname)
            .filter(DBUserNickname.nickname == username)
            .first()
        )
        if data:
            return True
        return False


def email_exists(email: str) -> bool:
    """Determine whether or not a email address already exists in the DB."""
    with transaction() as session:
        data = session.query(DBUser).filter(DBUser.email == email).first()
        if data:
            return True
        return False


def register(user_registration: domain.UserRegistration, ip_address: str,
             remote_host: str) -> Tuple[domain.User, domain.Authorizations]:
    """Add a new user to the database and return user data."""
    with transaction() as session:
        # Main user entry.
        db_user = DBUser(
            first_name=user_registration.name.forename,
            last_name=user_registration.name.surname,
            suffix_name=user_registration.name.suffix,
            email=user_registration.email,
            policy_class=DBPolicyClass.PUBLIC_USER,
            joined_ip_num=ip_address,
            joined_remote_host=remote_host,
            joined_date=now(),
            tracking_cookie='',  # TODO: how to set?
        )
        session.add(db_user)

        # Nickname is (apparently) where we keep the username.
        db_nick = DBUserNickname(
            user=db_user,
            nickname=user_registration.username,
            flag_valid=1,
            flag_primary=1
        )
        session.add(db_nick)

        def _has_group(group: str) -> int:
            return int(group in user_registration.profile.submission_groups)

        # TODO: where to put the new categories?
        db_profile = DBProfile(
            user=db_user,
            country=user_registration.profile.country,
            affiliation=user_registration.profile.organization,
            url=user_registration.profile.homepage_url,
            rank=user_registration.profile.rank,
            archive=user_registration.profile.default_archive,
            subject_class=user_registration.profile.default_subject,
            original_subject_classes='',
            flag_group_physics=_has_group('grp_physics'),
            flag_group_math=_has_group('grp_math'),
            flag_group_cs=_has_group('grp_cs'),
            flag_group_q_bio=_has_group('grp_q-bio'),
            flag_group_q_fin=_has_group('grp_q-fin'),
            flag_group_stat=_has_group('grp_stat'),
        )
        session.add(db_profile)

        db_pass = DBUserPassword(
            user=db_user,
            password_enc=hash_password(user_registration.password)
        )
        session.add(db_pass)
        session.commit()

        user = domain.User(
            user_id=str(db_user.user_id),
            username=db_nick.nickname,
            email=db_user.email,
            name=domain.UserFullName(
                forename=db_user.first_name,
                surname=db_user.last_name,
                suffix=db_user.suffix_name
            )
        )
        auths = domain.Authorizations(
            classic=compute_capabilities(db_user),
            scopes=get_scopes(db_user),
            endorsements=get_endorsements(user)
        )
        return user, auths
