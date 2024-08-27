from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

from modapi.config import config

if 'sqlite' in config.classic_db_uri:
    args = {"check_same_thread": False}
else:
    args = {}

engine = create_engine(config.classic_db_uri, echo=config.echo_sql, connect_args=args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def create_tables():
    """Create any missing tables.

    This is a synchronous call"""
    from sqlalchemy import create_engine
    import modapi.tables.arxiv_tables as arxiv_tables
    sync_url = config.classic_db_uri.replace('+aiomysql', '')
    sync_eng = create_engine(sync_url,
                             echo=config.echo_sql)
    arxiv_tables.metadata.create_all(bind=sync_eng)


def get_db():
    """Dependency for fastapi routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
