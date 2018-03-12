"""arXiv accounts database models."""
from sqlalchemy import BigInteger, Column, DateTime, Enum, \
    ForeignKey, Index, Integer, SmallInteger, String, Text, text
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy, Model
from typing import Any, NewType

dbx: SQLAlchemy = SQLAlchemy()


class TapirSession(dbx.Model):
    """
    Legacy arXiv session table.

        +----------------+-----------------+------+-------+---------+----------------+
        | Field          | Type            | Null | Key   | Default | Extra          |
        +----------------+-----------------+------+-------+---------+----------------+
        | session_id     | int(4) unsigned | NO   | PRI   | NULL    | auto_increment |
        | user_id        | int(4) unsigned | NO   | MUL   | 0       |                |
        | last_reissue   | int(11)         | NO   |       | 0       |                |
        | start_time     | int(11)         | NO   | MUL   | 0       |                |
        | end_time       | int(11)         | NO   | MUL   | 0       |                |
        +--------------+-------------------+------+-------+---------+----------------+
    """

    __tablename__ = 'tapir_sessions'

    session_id = Column(Integer, primary_key=True, autoincrement="auto")
    user_id = Column(ForeignKey('tapir_users.user_id'), nullable=False, index=True, server_default=text("'0'"))
    last_reissue = Column(Integer, nullable=False, server_default=text("'0'"))
    start_time = Column(Integer, nullable=False, index=True, server_default=text("'0'"))
    end_time = Column(Integer, nullable=False, index=True, server_default=text("'0'"))

    user = relationship('TapirUser')


class TapirSessionsAudit(TapirSession):
    """Legacy arXiv session audit table. Notably has a tracking cookie."""

    __tablename__ = 'tapir_sessions_audit'

    session_id = Column(ForeignKey('tapir_sessions.session_id'), primary_key=True, server_default=text("'0'"))
    ip_addr = Column(String(16), nullable=False, index=True, server_default=text("''"))
    remote_host = Column(String(255), nullable=False, server_default=text("''"))
    tracking_cookie = Column(String(255), nullable=False, index=True, server_default=text("''"))

class TapirUser(dbx.Model):
    """Legacy table that is a foreign key dependency of TapirSession."""
    
    __tablename__ = 'tapir_users'

    user_id = Column(Integer, primary_key=True)
    first_name = Column(String(50), index=True)
    last_name = Column(String(50), index=True)
    suffix_name = Column(String(50))
    share_first_name = Column(Integer, nullable=False, server_default=text("'1'"))
    share_last_name = Column(Integer, nullable=False, server_default=text("'1'"))
    email = Column(String(255), nullable=False, unique=True, server_default=text("''"))
    share_email = Column(Integer, nullable=False, server_default=text("'8'"))
    email_bouncing = Column(Integer, nullable=False, server_default=text("'0'"))
    policy_class = Column(ForeignKey('tapir_policy_classes.class_id'), nullable=False, index=True, server_default=text("'0'"))
    joined_date = Column(Integer, nullable=False, index=True, server_default=text("'0'"))
    joined_ip_num = Column(String(16), index=True)
    joined_remote_host = Column(String(255), nullable=False, server_default=text("''"))
    flag_internal = Column(Integer, nullable=False, index=True, server_default=text("'0'"))
    flag_edit_users = Column(Integer, nullable=False, index=True, server_default=text("'0'"))
    flag_edit_system = Column(Integer, nullable=False, server_default=text("'0'"))
    flag_email_verified = Column(Integer, nullable=False, server_default=text("'0'"))
    flag_approved = Column(Integer, nullable=False, index=True, server_default=text("'1'"))
    flag_deleted = Column(Integer, nullable=False, index=True, server_default=text("'0'"))
    flag_banned = Column(Integer, nullable=False, index=True, server_default=text("'0'"))
    flag_wants_email = Column(Integer, nullable=False, server_default=text("'0'"))
    flag_html_email = Column(Integer, nullable=False, server_default=text("'0'"))
    tracking_cookie = Column(String(255), nullable=False, index=True, server_default=text("''"))
    flag_allow_tex_produced = Column(Integer, nullable=False, server_default=text("'0'"))


class TapirPolicyClass(dbx.Model):
    """
    Legacy table that is a foreign key depency of TapirUse.

    TapirUse is itself a dependency of TapirSession.
    """

    __tablename__ = 'tapir_policy_classes'

    class_id = Column(SmallInteger, primary_key=True)
    name = Column(String(64), nullable=False, server_default=text("''"))
    description = Column(Text, nullable=False)
    password_storage = Column(Integer, nullable=False, server_default=text("'0'"))
    recovery_policy = Column(Integer, nullable=False, server_default=text("'0'"))
    permanent_login = Column(Integer, nullable=False, server_default=text("'0'"))
