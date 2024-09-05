"""Provides integration for the external user interface."""
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Depends, status, Request, HTTPException
from fastapi.responses import RedirectResponse, Response, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from arxiv.base import logging
from arxiv.auth.user_claims import ArxivUserClaims
from arxiv.auth.openid.oidc_idp import ArxivOidcIdpClient
from arxiv.auth.user_claims_to_legacy import create_tapir_session_from_user_claims
from arxiv.auth.legacy.sessions import invalidate as legacy_invalidate
from arxiv.db.models import TapirCountry
from arxiv.db import SessionLocal
from arxiv.auth.legacy.exceptions import NoSuchUser

# from arxiv.db import get_db

from . import get_current_user, get_db, get_current_user_or_none
import socket

def get_db():
    """Dependency for fastapi routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


logger = logging.getLogger(__name__)

router = APIRouter()

@router.get('/login')
def login(request: Request,
          current_user: Optional[dict] = Depends(get_current_user_or_none)
          ) -> Response:
    """User can log in with username and password, or permanent token."""
    # redirect to IdP
    idp: ArxivOidcIdpClient = request.app.extra["idp"]
    url = idp.login_url
    next_page = request.query_params.get('next_page', request.query_params.get('next', '/'))
    if next_page:
        url = url + "&state=" + urllib.parse.quote(next_page)
    if current_user:
        pass
    logger.info(f"Login URL: {url}")
    return RedirectResponse(url)


@router.get('/callback')
async def oauth2_callback(request: Request,
                          _db = Depends(get_db)
                          ) -> Response:
    """User can log in with username and password, or permanent token."""
    code = request.query_params.get('code')
    logger.debug("callback code: %s", repr(code))
    if code is None:
        logger.warning("error: %s", repr(request.query_params))
        request.session.clear()
        return Response(status_code=status.HTTP_200_OK)

    idp: ArxivOidcIdpClient = request.app.extra["idp"]
    user_claims: ArxivUserClaims = idp.from_code_to_user_claims(code)

    session_cookie_key = request.app.extra['AUTH_SESSION_COOKIE_NAME']
    classic_cookie_key = request.app.extra['CLASSIC_COOKIE_NAME']

    if user_claims is None:
        logger.warning("Getting user claim failed. code: %s", repr(code))
        request.session.clear()
        # return Response(status_code=status.HTTP_401_UNAUTHORIZED)
        response = RedirectResponse(request.app.extra['ARXIV_URL_LOGIN'])
        response.set_cookie(session_cookie_key, '', max_age=0)
        response.set_cookie(classic_cookie_key, '', max_age=0)
        return response

    logger.debug("User claims: user id=%s, email=%s", user_claims.user_id, user_claims.email)

    # NG cookie
    secret = request.app.extra['JWT_SECRET']
    token = user_claims.encode_jwt_token(secret)

    # legacy cookie
    tapir_cookie = ""
    client_ip = request.headers.get("x-real-ip", request.client.host)
    client_host = ''
    logger.info("User claims: ip=%s", client_ip)
    try:
        client_host = socket.gethostbyaddr(client_ip)[0]
    except Exception as _exc:
        logger.info('client host resolve failed for ip %s', client_ip)
        pass

    tapir_session = None
    try:
        tapir_cookie, tapir_session = create_tapir_session_from_user_claims(user_claims, client_host, client_ip)
    except NoSuchUser:
        # Likely the user exist on keycloak but not in tapir user.
        # Since newer apps should work without
        logger.info("User exists on keycloak but not on tapir", exc_info=False)
        pass
    except Exception as exc:
        logger.error("Setting up Tapir session failed.", exc_info=exc)
        pass

    if tapir_session is not None:
        logger.debug("tapir_session: %s", repr(tapir_session))

    next_page = urllib.parse.unquote(request.query_params.get("state", "/"))  # Default to root if not provided
    logger.debug("callback success: next page: %s", next_page)
    response: Response = RedirectResponse(next_page, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(session_cookie_key, token, max_age=3600, samesite="lax")
    # response.set_cookie("token", token, max_age=3600)
    if tapir_cookie:
        logger.info('%s=%s',classic_cookie_key, tapir_cookie)
        response.set_cookie(classic_cookie_key, tapir_cookie, max_age=3600, samesite="lax")
    else:
        logger.info('%s=<EMPTY>',classic_cookie_key)
        response.set_cookie(classic_cookie_key, '', max_age=0, samesite="lax")
    # ui_response = requests.get(idp.user_info_url,
    #                            headers={"Authorization": "Bearer {}".format(user_claims.access_token)})
    return response


@router.get('/refresh')
def login(request: Request,
          current_user: Optional[dict] = Depends(get_current_user_or_none)
          ) -> Response:
    """User can log in with username and password, or permanent token."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    # redirect to IdP
    idp: ArxivOidcIdpClient = request.app.extra["idp"]
    url = idp.refsesh_url
    logger.info(f"Login URL: {url}")
    return RedirectResponse(url)


@router.get('/logout')
async def logout(request: Request,
                 _db=Depends(get_db),
                 current_user: dict = Depends(get_current_user_or_none)) -> Response:
    """Log out of arXiv."""
    default_next_page = request.app.extra['ARXIV_URL_HOME']
    next_page = request.query_params.get('next_page', request.query_params.get('next', default_next_page))
    response = RedirectResponse(next_page, status_code=status.HTTP_303_SEE_OTHER)
    session_cookie_key = request.app.extra['AUTH_SESSION_COOKIE_NAME']
    legacy_cookie_key = request.app.extra['CLASSIC_COOKIE_NAME']

    if current_user is not None:
        logger.debug('Request to log out, then redirect to %s', next_page)
        idp: ArxivOidcIdpClient = request.app.extra["idp"]
        if not idp.logout_user(current_user):
            # Failed to log out, so keep the cookies
            return response

    response.set_cookie(session_cookie_key, "", max_age=0)

    #
    classic_cookie = request.cookies.get(legacy_cookie_key)
    if classic_cookie:
        try:
            legacy_invalidate(classic_cookie)
            response.set_cookie(legacy_cookie_key, "", max_age=0)
        except Exception as exc:
            logger.error("Invalidating legacy session failed.", exc_info=exc)
            pass

    return response


@router.get('/token-names')
async def get_token_names(request: Request) -> JSONResponse:
    session_cookie_key = request.app.extra['AUTH_SESSION_COOKIE_NAME']
    classic_cookie_key = request.app.extra['CLASSIC_COOKIE_NAME']
    return {
        "session": session_cookie_key,
        "classic": classic_cookie_key
    }


@router.get('/check-db')
async def check_db(request: Request,
                   db: Session = Depends(get_db)) -> JSONResponse:
    count = db.query(func.count(TapirCountry.digraph)).scalar()
    return {"count": count}
