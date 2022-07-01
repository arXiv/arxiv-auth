"""Special pytest fixture configuration file.

This file automatically provides all fixtures defined in it to all
pytest tests in this directory and sub directories.

See https://docs.pytest.org/en/6.2.x/fixture.html#conftest-py-sharing-fixtures-across-multiple-files
"""
import pytest
import pytest_asyncio
import importlib
from typing import Optional
import logging

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from pathlib import Path

from arxiv.cloud_auth.userstore import UserStore, UserStoreDB
from arxiv.cloud_auth.domain import User
import arxiv.cloud_auth.fastapi.auth as auth

DB_FILE = "./pytest.db"

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"

CONNECT_ARGS = (
    {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

DELETE_DB_FILE_ON_EXIT = True


def escape_bind(stmt):
    return stmt.replace(r":0", "\:0")


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=CONNECT_ARGS)
    return engine


@pytest.fixture(scope="session")
def user_db(engine):
    print("Making tables...")
    try:
        import arxiv.cloud_auth.userstore_test_tables as tables

        tables.metadata.create_all(bind=engine)
        print("Done making tables. Starting load of data.")
        tables.load_test_data(engine)
        print("Done loading test data.")
        yield engine
    finally:  # cleanup
        if DELETE_DB_FILE_ON_EXIT:
            Path(DB_FILE).unlink(missing_ok=True)
            print(f"Cleaning up: Deleted test db file at {DB_FILE}.")


@pytest.fixture(scope="session")
def get_test_db(user_db):
    # See https://fastapi.tiangolo.com/advanced/testing-database
    engine = user_db
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    return override_get_db


@pytest.fixture
def secret():
    return "testing_secret"


@pytest.fixture
def userstore(get_test_db):
    _userstore = UserStoreDB()
    return UserStore(_userstore, get_test_db)


@pytest.fixture
def api_auth(userstore, secret):
    return auth.AuthorizedUser(secret, "testingAudience", userstore)


@pytest_asyncio.fixture
async def fastapi(api_auth):
    """Returns a fast-api app"""
    app = FastAPI()

    @app.get("/")
    async def root(user: Optional[User] = Depends(api_auth)) -> str:
        return user

    client = TestClient(app)
    return client
