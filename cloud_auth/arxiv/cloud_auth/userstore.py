"""Caching of arXiv mod and admin users"""

from types import GeneratorType
from typing import Optional, Dict, List, Tuple, Union, Callable
from dataclasses import dataclass, field
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from .domain import User


log = logging.getLogger(__name__)

from pydantic import BaseModel


class UserStoreDB():
    """Userstore that does not fully handle categories or archives.

    In most cases ``UserStore`` should be used instead.

    This is intended to be used where full handling of categories is
    not needed or where additoinal code will handle active categories
    and archives. See ``_cats_and_archives`` for more details.

    The intent here is to avoid the need for arxiv-base to avoid
    dependency clashes.
    """

    _users: Dict[int, User] = {}
    """Cache for users"""

    def __init__(self):
        self._users = {}

    def invalidate_user(self, user_id: int) -> bool:
        """Remove user id from cache. Returns bool if id was in cache"""
        if user_id in self._users:
            del self._users[user_id]
            return True
        else:
            return False

    def getuser(self, user_id: int, db: Session) -> Optional[User]:
        """Gets a user by user_id"""
        if user_id in self._users:
            return self._users[user_id]

        return self._getfromdb(user_id, db)

    def getuser_by_nick(self, nick: str, db: Session) -> Optional[User]:
        by_nick = [user for user in self._users.values() if user.username == nick]
        if len(by_nick) == 1:
            return by_nick[0]

        if len(by_nick) > 1:
            log.error(f"{len(by_nick)} users with the same nickname {nick[:10]}")
            return None

        return self._getfromdb_by_nick(nick, db)


    def getuser_by_email(self, email: str, db: Session) -> Optional[User]:
        by_email = [user for user in self._users.values() if user.email == email]
        if len(by_email) == 1:
            return by_email[0]
        if len(by_email) > 1:
            log.error(f"{len(by_email)} users with the same emailname {email[:10]}")
            return None

        return self._getfromdb_by_email(email, db)


    def _getfromdb_by_email(self, email: str, db: Session) -> Optional[User]:
        query = """SELECT tapir_users.user_id FROM tapir_users
        WHERE tapir_users.email = :email"""
        rs = list(db.execute(text(query), {"email": email}))
        if not rs:
            log.debug("no user found in DB for email %s", email[:10])
            return None

        return self._getfromdb(rs[0]["user_id"], db)

    def _getfromdb_by_nick(self, nick: str, db: Session) -> Optional[User]:
        query = """
        SELECT tapir_nicknames.user_id
        FROM tapir_nicknames
        WHERE tapir_nicknames.nickname = :nick"""

        rs = list(db.execute(text(query), {"nick": nick}))
        if not rs:
            log.debug("no user found in DB for nickname %s", nick[:10])
            return None

        return self._getfromdb(rs[0]["user_id"], db)

    def to_name(self, first_name, last_name):
        """Display name from first_name and last_name"""
        return f"{first_name} {last_name}".strip()

    def _getfromdb(self, user_id: int, db: Session) -> Optional[User]:
        user_query = """
        SELECT
        hex(tapir_users.first_name) as first_name,
        hex(tapir_users.last_name) as last_name,
        tapir_users.email as email,
        tapir_nicknames.nickname, tapir_users.flag_edit_users
        FROM tapir_users
        JOIN tapir_nicknames ON tapir_users.user_id = tapir_nicknames.user_id
        WHERE tapir_users.user_id = :userid"""

        rs = list(db.execute(text(user_query), {"userid": user_id}))
        if not rs:
            return None

        cats, archives = self._cats_and_archives(user_id, db)
        name = self.to_name(bytes.fromhex(rs[0]["first_name"]).decode("utf-8"),
                            bytes.fromhex(rs[0]["last_name"]).decode("utf-8"))
        ur = User(
            user_id=user_id,
            name=name, 
            username=rs[0]["nickname"],
            email=rs[0]["email"],
            is_admin=bool(rs[0]["flag_edit_users"]),
            is_moderator=bool(cats or archives),
            moderated_categories=cats,
            moderated_archives=archives,
        )

        self._users[ur.user_id] = ur
        return ur


    def _cats_and_archives(
        self, user_id: int, db: Session
    ) -> Tuple[List[str], List[str]]:
        """Archives and categories for the moderator.

        NOTE: This only returns the raw results from arXiv_moderators
        and does not account for subsumed archive like categories.
        
        This may need to be filtered to just ARCHIVES_ACTIVE or
        CATEGORIES_ACTIVE if that is what you need. Like if you want
        to show a moderator the list of areas they would consider
        themselves a moderator of.

         Code to do that would be, after installing arxiv-base:
            
            from arxiv.taxonomy.definitions import ARCHIVES_ACTIVE, CATEGORIES, CATEGORIES_ACTIVE
            def active(user):
                archives = [arch for arch in user.moderated_archives
                            if arch in ARCHIVES_ACTIVE]
                # normal categories like cs.LG
                cats = [cat for cat in usesr.moderated_categories 
                        if cat in CATEGORIES_ACTIVE]
                # Archive like categories. ex. hep-ph, gr-qc, nucl-ex, etc.
                # Don't include inactive archives since they should have been
                # subsumed (ex cmp-lg -> cs.LG) or turned to archives (ex cond-mat).
                cats.extend([arch for arch in user.moderated_archives
                             if arch in CATEGORIES_ACTIVE])
               return (archives, cats)

        import 
        Returns
        -------
        Tuple of ( categories, archives)


        The archvies where the arxiv_moderators table has just an
        archive column value and not subject_class value. This may
        have subject categoires like hep-ph.

        The categories where in the arXiv_moderators table has both a archvie
        and a subject_class.

        """
        cat_mod_query = """SELECT archive as 'arch', subject_class as 'cat'
        FROM arXiv_moderators WHERE user_id = :userid"""
        mod_rs = list(db.execute(text(cat_mod_query), {"userid": user_id}))
        
        archives = [row["arch"] for row in mod_rs if row["arch"] and not row["cat"]]
        cats = [f"{row['arch']}.{row['cat']}" for row in mod_rs
                if row["arch"] and row["cat"]]
        return (cats, archives)



class UserStore():
    """UserStoreDb with db partially applied.

    db can be either a Session or a function that returns Sessions."""
    def __init__(self, userstore: UserStoreDB,
                 db: Union[Session, Callable[[],Session]]):


        self.userstore = userstore
        if isinstance(db, Session):
            self.get_db = lambda :db        
        else:
            def to_db():
                xdb = db()
                if isinstance(xdb, GeneratorType):
                    return next(xdb)
                else:
                    return xdb
            self.get_db = to_db


    def invalidate_user(self, user_id: int) -> bool:
        """Remove user id from cache. Returns bool if id was in cache"""
        return self.userstore.invalidate_user(user_id)

    def getuser(self, user_id: int) -> Optional[User]:
        """Gets a user by user_id"""
        return self.userstore.getuser(user_id, self.get_db())

    def getuser_by_nick(self, nick: str) -> Optional[User]:
        return self.userstore.getuser_by_nick(nick, self.get_db())

    def getuser_by_email(self, email: str) -> Optional[User]:
        return self.userstore.getuser_by_email(email, self.get_db())

    def to_name(self, first_name, last_name):
        """Display name from first_name and last_name"""
        return self.userstore.to_name(first_name, last_name)
