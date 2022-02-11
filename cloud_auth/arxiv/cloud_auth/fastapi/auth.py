import logging
import secrets
import sys
from typing import Optional, Literal, Callable
from dataclasses import dataclass

from fastapi import Cookie, Depends, Header, HTTPException

from ..gcp_token_check import verify_token, email_from_idinfo
from ..jwt import decode
from ..userstore import UserStore
from ..domain import Auth, RawAuth, User

log = logging.getLogger(__name__)


get_userstore: Optional[Callable[[], UserStore]] = None
"""Set this to configure the Userstore

It should be a Callable return or yield a Userstore object.
"""

jwt_secret_config: Optional[str] = None
"""Set this to configure the JWT secret. This can be a string or a pydantic secret"""

audience: Optional[str] = None
"""Set this to configure the audience or Client ID this auth should accept"""

async def jwt_secret() -> Optional[str]:
    """Gets the JWT secret"""
    if not jwt_secret_config:
        raise RuntimeError("jwt_secret_config not set in auth")
    if hasattr(jwt_secret_config, "get_secret_value"):
        return jwt_secret_config.get_secret_value()
    else:
        return jwt_secret_config


def mod_header_user() -> Optional[User]:
    """Mod keys are disabled by default"""
    return None


def enable_modkey():
    """Enable mod keys for testing"""

    def mod_header_user_enabled(
        modkey: Optional[str] = Header(None),
        userstore: UserStore = Depends(get_userstore),
    ) -> Optional[User]:
        """Gets the modkey header that is used for testing"""
        if not modkey or not modkey.startswith("mod-"):
            return None
        else:
            return userstore.getuser_by_nick(modkey.lstrip("mod-"))

    log.warning("Enabling modkey in %s", __name__)
    module_obj = sys.modules[__name__]
    setattr(module_obj, "mod_header_user", mod_header_user_enabled)


async def ng_jwt_cookie(
    ARXIVNG_SESSION_ID: Optional[str] = Cookie(None),
) -> Optional[RawAuth]:
    """Gets the NG session undecoded JWT via a HTTP cookie

    As of Feb 2022 arxiv-check uses the ARXIVNG_SESSION_ID cookie for auth.
    Mods will log in to arxiv.org/login, get the cookie set, go to mod.arxiv.org/ui,
    and that will make REST calls to mod.arxiv.org/{ENDPOINT}.

    The main difficulty of this compard to a Authorization header is
    handling the cookie so the browser will serve it to the
    API. Debugging that is painful.

    """
    log.debug("Got a arxiv NG cookie named ARXIVNG_SESSION_ID")
    if ARXIVNG_SESSION_ID:
        return RawAuth(
            rawjwt=ARXIVNG_SESSION_ID,
            rawheader=None,
            via="cookie",
            key="ARXIVNG_SESSION_ID",
        )


async def jwt_header(Authorization: Optional[str] = Header(None),) -> Optional[RawAuth]:
    """Gets JWT from Authorization Bearer header."""
    if not Authorization:
        return None

    parts = Authorization.split()
    if parts[0].lower() != "bearer":
        log.debug("Authorization header Failed, lacked bearer")
        return None
    if len(parts) != 2:
        log.debug("Authorization header Failed, not 2 parts")
        return None
    else:
        log.debug("Got header:Authorization with a JWT")
        log.debug("jwt_header(): %s", Authorization)
        return RawAuth(
            rawjwt=parts[1], rawheader=Authorization, via="header", key="Authorization",
        )


async def rawauth(
    cookie: Optional[RawAuth] = Depends(ng_jwt_cookie),
    header: Optional[RawAuth] = Depends(jwt_header),
) -> Optional[RawAuth]:
    """Gets the JWT from cookie or header"""
    if cookie or header:
        log.debug("rawauth() using %s", "cookie" if cookie else "header")
        return cookie or header



class AuthorizedUser:
    """Check ensure authenticatoin and user is a mod or admin and gets a
    User object.

    This will try to decode with the JWT_SECRET then try GCP.

    This is the depends that you almost always want to use in modapi3.
    Use this if you want the request authenticated and you want to
    ensure a mod or admin and you also want a User object.
    """
    def __init__(self, secret: str, audience: str, userstore: UserStore):
        self.secret = secret
        self.audience = audience
        self.userstore = userstore

    def decode_ng_jwt(self, jwt) -> Optional[User]:
        try:
            data = decode(jwt, self.secret)
            # FYI: don't try GCP if the JWT decodes with JWT_SECRET
            if data:
                log.debug("decode_ng_jwt(), found and decoded JWT with JWT_SECRET")
                user_id = data["user_id"]
                user = self.userstore.getuser(user_id)
                if not user:
                    log.debug("decode_ng_jwt() Failed: user %s is does not exist", user_id)
                    return None
                else:
                    log.debug("decode_ng_jwt() User found in NG JWT")
                    return user
        except Exception as ex:
            log.debug("decode_ng_jwt() Exception during NG JWT %s", ex)


    async def verify_gcp(self, jwt:str) -> Optional[User]:
        try:
            idinfo = verify_token(self.audience, jwt)
            if not idinfo:
                log.debug("verity_gcp() failed: Invalid JWT, No idinfo from GCP")
                return None
            else:
                log.debug("verity_gcp(): valid JWT from GCP")
                email = email_from_idinfo(idinfo)
                if not email:
                    log.debug("verity_gcp() failed: no email from GCP")
                    return None
                user = self.userstore.getuser_by_email(email)
                if user:
                    log.debug("verity_gcp() found arXiv user via GCP JWT")
                    return user
                else:
                    log.debug("verity_gcp() failed: no user with email %s", email)
                    return None
        except Exception as ex:
            log.debug("verity_gcp() Exception during GCP JWT validation: %s", ex)


    async def __call__(self, header: RawAuth = Depends(rawauth)):
        try:
            if not header:
                log.debug("auth() Failed, no rawauth")
                raise Exception("No raw auth data ")
            user = self.decode_ng_jwt(header.rawjwt) or await self.verify_gcp(header.rawjwt)
            if not user:
                raise Exception("invaild auth data")

            # if mod and (mod.is_admin or mod.is_moderator):
            #     log.debug("auth_user(): Success via mod key")
            #     return mod
            if user and (user.is_admin or user.is_moderator):
                log.debug("Success")
                return user
            else:
                log.debug("Failed: User is not an admin or mod")
                raise Exception("User is not mod or admin")
        except Exception as ex:
            raise HTTPException(status_code=401, detail="Unauthorized") from ex



