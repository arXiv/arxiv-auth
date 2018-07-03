"""Provide methods for working with user accounts."""

from typing import Tuple, Any
from .. import domain
from .util import transaction
from .exceptions import NoSuchUser
from .models import DBUser, DBUserNickname, DBProfile


def get_user_by_id(user_id: str) -> domain.User:
    """Load user data from the database."""
    db_user, db_nick, db_profile = _get_user_data(user_id)
    user = domain.User(
        user_id=str(db_user.user_id),
        username=db_nick.nickname,
        email=db_user.email,
        name=domain.UserFullName(
            forename=db_user.first_name,
            surname=db_user.last_name,
            suffix=db_user.suffix_name
        ),
        profile=db_profile.to_domain()
    )
    return user


def update_user(user: domain.User) -> None:
    """Update a user in the database."""
    db_user, db_nick, db_profile = _get_user_data(user.user_id)
    _update_field(db_nick.nickname, user.username)
    _update_field(db_user.email, user.email)
    _update_field(db_user.first_name, user.name.forename)
    _update_field(db_user.last_name, user.name.surname)
    _update_field(db_user.suffix_name, user.name.suffix)
    _update_field(db_profile.origanization, user.profile.origanization)
    _update_field(db_profile.country, user.profile.country)
    _update_field(db_profile.rank, user.profile.rank)
    _update_field(db_profile.rank, user.profile.rank)


def _update_field(to_update: Any, update_with: Any) -> None:
    if to_update != update_with:
        to_update = update_with


def _get_user_data(user_id: str) -> Tuple[DBUser, DBUserNickname, DBProfile]:
    with transaction() as session:
        db_user, db_nick, db_profile = (
            session.query(DBUser, DBUserNickname, DBProfile)
            .filter(DBUser.user_id == user_id)
            .filter(DBUser.flag_approved == 1)
            .filter(DBUser.flag_deleted == 0)
            .filter(DBUser.flag_banned == 0)
            .filter(DBUserNickname.flag_primary == 1)
            .filter(DBUserNickname.flag_valid == 1)
            .filter(DBUserNickname.user_id == DBUser.user_id)
            .filter(DBProfile.user_id == DBUser.user_id)
            .first()
        )
        if not db_user:
            raise NoSuchUser('User does not exist')
    return db_user, db_nick, db_profile
