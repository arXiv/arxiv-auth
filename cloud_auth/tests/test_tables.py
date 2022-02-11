"""Test db with resonable simulation of necessary legacy tables.

Some foreign keys have been excluded."""

from sqlalchemy import (
    BINARY,
    CHAR,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    MetaData,
    String,
    TIMESTAMP,
    Table,
    Text,
    text,
    UniqueConstraint,
    MetaData,
    BigInteger,
    Numeric,
    Integer,
    insert,
)

metadata = MetaData()

tapir_users = Table(
    "tapir_users",
    metadata,
    Column("user_id", Integer(), primary_key=True),
    Column("first_name", String(50), index=True),
    Column("last_name", String(50), index=True),
    Column("suffix_name", String(50)),
    Column("share_first_name", Integer(), nullable=False, server_default=text("'1'")),
    Column("share_last_name", Integer(), nullable=False, server_default=text("'1'")),
    Column(
        "email", String(255), nullable=False, unique=True, server_default=text("''")
    ),
    Column("share_email", Integer(), nullable=False, server_default=text("'8'")),
    Column("email_bouncing", Integer(), nullable=False, server_default=text("'0'")),
    # Column('policy_class', ForeignKey('tapir_policy_classes.class_id'), nullable=False, index=True, server_default=text("'0'")),
    Column(
        "joined_date",
        Integer(),
        nullable=False,
        index=True,
        server_default=text("'0'"),
    ),
    Column("joined_ip_num", String(16), index=True),
    Column(
        "joined_remote_host", String(255), nullable=False, server_default=text("''")
    ),
    Column(
        "flag_internal",
        Integer(),
        nullable=False,
        index=True,
        server_default=text("'0'"),
    ),
    Column(
        "flag_edit_users",
        Integer(),
        nullable=False,
        index=True,
        server_default=text("'0'"),
    ),
    Column("flag_edit_system", Integer(), nullable=False, server_default=text("'0'")),
    Column(
        "flag_email_verified", Integer(), nullable=False, server_default=text("'0'")
    ),
    Column(
        "flag_approved",
        Integer(),
        nullable=False,
        index=True,
        server_default=text("'1'"),
    ),
    Column(
        "flag_deleted",
        Integer(),
        nullable=False,
        index=True,
        server_default=text("'0'"),
    ),
    Column(
        "flag_banned",
        Integer(),
        nullable=False,
        index=True,
        server_default=text("'0'"),
    ),
    Column("flag_wants_email", Integer(), nullable=False, server_default=text("'0'")),
    Column("flag_html_email", Integer(), nullable=False, server_default=text("'0'")),
    Column(
        "tracking_cookie",
        String(255),
        nullable=False,
        index=True,
        server_default=text("''"),
    ),
    Column(
        "flag_allow_tex_produced",
        Integer(),
        nullable=False,
        server_default=text("'0'"),
    ),
    Column(
        "flag_can_lock",
        Integer(),
        nullable=False,
        index=True,
        server_default=text("'0'"),
    ),
)

tapir_nicknames = Table(
    "tapir_nicknames",
    metadata,
    Column("nick_id", Integer(), primary_key=True),
    Column(
        "nickname", String(20), nullable=False, unique=True, server_default=text("''"),
    ),
    Column(
        "user_id",
        ForeignKey("tapir_users.user_id"),
        nullable=False,
        server_default=text("'0'"),
    ),
    Column("user_seq", Integer(), nullable=False, server_default=text("'0'")),
    Column(
        "flag_valid", Integer(), nullable=False, index=True, server_default=text("'0'"),
    ),
    Column("role", Integer(), nullable=False, index=True, server_default=text("'0'")),
    Column("policy", Integer(), nullable=False, index=True, server_default=text("'0'")),
    Column("flag_primary", Integer(), nullable=False, server_default=text("'0'")),
    Index("user_id", "user_id", "user_seq", unique=True),
)

arXiv_moderators = Table(
    "arXiv_moderators",
    metadata,
    Column(
        "user_id",        
        ForeignKey("tapir_users.user_id"),
        nullable=False,
        index=True,
        server_default=text("'0'"),
    ),
    Column(
        "archive",
        Integer(),
        # ForeignKey("arXiv_archive_group.archive_id"),
        nullable=False,
        server_default=text("''"),
    ),
    Column("subject_class", String(16), nullable=False, server_default=text("''")),
    Column("is_public", Integer(), nullable=False, server_default=text("'0'")),
    Column("no_email", Integer(), index=True, server_default=text("'0'")),
    Column("no_web_email", Integer(), index=True, server_default=text("'0'")),
    Column("no_reply_to", Integer(), index=True, server_default=text("'0'")),
    Column("daily_update", Integer(), server_default=text("'0'")),
    # ForeignKeyConstraint(
    #     ["archive", "subject_class"],
    #     ["arXiv_categories.archive", "arXiv_categories.subject_class"],
    # ),
    Index(
        "arxiv_moderator_idx_user_id",
        "archive",
        "subject_class",
        "user_id",
        unique=True,
    ),
)

def load_test_data(engine):
    rows = [
        [tapir_users, {'user_id':1, 'first_name':'Paul', 'last_name':'Houle', 'email':'bh@com'}, "A user"],
        [tapir_nicknames, {'user_id':1, 'nick_id':101, 'nickname':'paulhoule'}, "A user nickname"],

        [tapir_users, {'user_id':2, 'first_name':'Skunk', 'last_name':'Skunk', 'email':'sk@s.org'}, "A skunk"],
        [tapir_nicknames, {'user_id':2, 'nick_id':102, 'nickname':'skunk'}, "Skunk user nickname"],
        [arXiv_moderators, {'user_id':2, 'archive':'bicycles', 'subject_class':'chopped'}, "Skunk mod1"],
        [arXiv_moderators, {'user_id':2, 'archive':'bicycles', 'subject_class':'tall'}, "Skunk mod2"],

        [tapir_users, {'user_id':3, 'first_name':'Gropo', 'last_name':'unknown', 'email':'gropo@s.org'}, "Gropo"],
        [tapir_nicknames, {'user_id':3, 'nick_id':103, 'nickname':'gropo'}, "Gropo user nickname"],
        [arXiv_moderators, {'user_id':3, 'archive':'music', 'subject_class':'ween'}, "gropo mod1"],
        [arXiv_moderators, {'user_id':3, 'archive':'bicycles', 'subject_class':'tall'}, "gropo mod2"],
        [arXiv_moderators, {'user_id':3, 'archive':'onions' }, "gropo mod3"],

        [tapir_users, {'user_id':4, 'first_name':'Rockstar', 'last_name':'unknown', 'email':'rs@s.org'}, "A rockstar"],
        [tapir_nicknames, {'user_id':4, 'nick_id':104, 'nickname':'rockstar'}, "Rockstar user nickname"],
        [arXiv_moderators, {'user_id':4, 'archive':'crew'}, "Rockstar mod1"],

        [tapir_users, {'user_id':5, 'first_name':'Jīngāng', 'last_name':'Jīng', 'email':'ds@s.org'}, "A user with UTF8"],
        [tapir_nicknames, {'user_id':5, 'nick_id':105, 'nickname':'金剛經'}, "金剛經 user nickname"],
        [arXiv_moderators, {'user_id':5, 'archive': '금강경'}, "金剛經 mod1"],

        [tapir_users, {'user_id':6, 'first_name':'random', 'last_name':'reader', 'email':'rreader@example.com'}, "A reader, non mod user"],
        [tapir_nicknames, {'user_id':6, 'nick_id':106, 'nickname':'randomreader'}, "A user nickname"],

        [tapir_users, {'user_id':7, 'first_name':'qa-tools-sq', 'last_name':'', 'email':'qa-tools-sa@arxiv-proj.iam.gserviceaccount.com', 'flag_edit_users': True }, "qa-tools-sa"],
        [tapir_nicknames, {'user_id':7, 'nick_id':107, 'nickname':'qa-tools-sq'}, "sa nickname"],
        
    ]

    for idx, row in enumerate(rows):
        table, values, comment = row
        try:
            engine.execute(insert(table).values(**values))
        except Exception as ex:
            raise Exception(f"Error while inserting {comment}", ex)
        
        
USER_ID_NO_PRIV = 6
