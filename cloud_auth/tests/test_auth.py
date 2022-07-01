import pytest
import logging

from arxiv.cloud_auth.domain import User
from fastapi.exceptions import HTTPException
from arxiv.cloud_auth.jwt import user_jwt

import arxiv.cloud_auth.fastapi.auth as auth


@pytest.mark.asyncio
async def test_unauth(api_auth):
    with pytest.raises(HTTPException):
        await api_auth(None)


def test_modkey(api_auth):
    assert auth.mod_header_user() == None
    auth.enable_modkey()

    class FakeUS:
        def getuser_by_nick(self, nick):
            return "GOT_IT"

    assert auth.mod_header_user("mod-skunk", FakeUS()) == "GOT_IT"


@pytest.mark.asyncio
async def test_cookie_to_user_auth(api_auth, secret):
    cookie = user_jwt(3, secret)
    rawauth = await auth.ng_jwt_cookie(cookie)
    assert rawauth
    user = await api_auth(rawauth)
    assert user
