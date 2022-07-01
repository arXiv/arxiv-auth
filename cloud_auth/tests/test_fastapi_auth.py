import pytest
import logging

from arxiv.cloud_auth.userstore_test_tables import USER_ID_NO_PRIV

import arxiv.cloud_auth.fastapi.auth as auth
from arxiv.cloud_auth.jwt import user_jwt

auth.log.setLevel(logging.DEBUG)


def test_auth(fastapi, secret):
    res = fastapi.get("/")
    assert res.status_code == 401 or res.json() == {}  # Should be auth protected

    res = fastapi.get("/", cookies={"ARXIVNG_SESSION_ID": "BOGUS"})
    assert res.status_code == 401  # should not get even with bogus SESSION_ID

    res = fastapi.get("/", cookies={"ARXIVNG_SESSION_ID": user_jwt(0, secret)})
    assert res.status_code == 401  # should not get even with bogus SESSION_ID

    res = fastapi.get("/", headers={"Authorization": user_jwt(0, secret)})
    assert res.status_code == 401

    res = fastapi.get("/", headers={"Authorization": "Bearer " + user_jwt(0, secret)})
    assert res.status_code == 401

    res = fastapi.get("/", headers={"Authorization": "Bearer BOGUS"})
    assert res.status_code == 401

    res = fastapi.get("/", headers={"Authorization": "Bearer BOGUS BOGUS"})
    assert res.status_code == 401

    res = fastapi.get("/", headers={"Authorization": "Bearer"})
    assert res.status_code == 401

    res = fastapi.get("/", headers={"Authorization": ""})
    assert res.status_code == 401


def test_unprivileged_user(fastapi, secret):
    res = fastapi.get(
        "/", cookies={"ARXIVNG_SESSION_ID": user_jwt(USER_ID_NO_PRIV, secret)}
    )
    assert res.status_code == 401

    res = fastapi.get(
        "/", headers={"Authorization": "Bearer " + user_jwt(USER_ID_NO_PRIV, secret)}
    )
    assert res.status_code == 401


def test_mod(fastapi, secret):
    res = fastapi.get("/", headers={"Authorization": "Bearer " + user_jwt(2, secret)})
    assert res.status_code == 200
    assert res.json() is not None
    user = res.json()
    assert user is not None
    assert "name" in user and user["name"] == "Skunk Skunk"
    assert "is_moderator" in user and user["is_moderator"]
    assert "is_admin" in user and not user["is_admin"]
    assert user["moderated_archives"] == []
    assert set(user["moderated_categories"]) == set(
        ["bicycles.chopped", "bicycles.tall"]
    )
