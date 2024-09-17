"""Provides integration for the external user interface."""
import urllib.parse
from typing import Optional, Tuple, Literal, Any

from fastapi import APIRouter, Depends, status, Request, HTTPException
from fastapi.responses import RedirectResponse, Response, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from arxiv.auth.auth.exceptions import UnknownSession
from arxiv.base import logging
from arxiv.auth.user_claims import ArxivUserClaims
from arxiv.auth.openid.oidc_idp import ArxivOidcIdpClient
from arxiv.auth.legacy.sessions import invalidate as legacy_invalidate

from . import get_current_user_or_none, get_db

from .sessions import create_tapir_session


def cookie_params(request: Request) -> Tuple[str, str, Optional[str], bool, Literal["lax", "none"]]:
    return (
        request.app.extra['AUTH_SESSION_COOKIE_NAME'],
        request.app.extra['CLASSIC_COOKIE_NAME'],
        request.app.extra.get('DOMAIN'),
        request.app.extra.get('SECURE', True),
        request.app.extra.get('SAMESITE', "lax"))


logger = logging.getLogger(__name__)

router = APIRouter()

@router.get('/login')
async def login(request: Request,
          current_user: Optional[ArxivUserClaims] = Depends(get_current_user_or_none)
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
    user_claims: Optional[ArxivUserClaims] = idp.from_code_to_user_claims(code)

    session_cookie_key, classic_cookie_key, domain, secure, samesite = cookie_params(request)

    if user_claims is None:
        logger.warning("Getting user claim failed. code: %s", repr(code))
        request.session.clear()
        # return Response(status_code=status.HTTP_401_UNAUTHORIZED)
        response = RedirectResponse(request.app.extra['ARXIV_URL_LOGIN'])
        #response.set_cookie(session_cookie_key, '', max_age=0, domain=domain, path="/",
        #                    secure=secure, samesite=samesite)
        #response.set_cookie(classic_cookie_key, '', max_age=0, domain=domain, path="/",
        #                    secure=secure, samesite=samesite)
        return response

    logger.debug("User claims: user id=%s, email=%s", user_claims.user_id, user_claims.email)

    # legacy cookie and session
    client_ip = request.headers.get("x-real-ip", request.client.host)
    tapir_cookie, tapir_session = create_tapir_session(user_claims, client_ip)

    # NG cookie
    #if tapir_cookie is not None:
    #    user_claims.set_tapir_cookie(tapir_cookie)

    # Set up cookies
    next_page = urllib.parse.unquote(request.query_params.get("state", "/"))  # Default to root if not provided
    logger.debug("callback success: next page: %s", next_page)

    response = make_cookie_response(request, user_claims, tapir_cookie, next_page)
    return response


@router.get('/refresh')
async def refresh_token(
        request: Request,
        current_user: Optional[ArxivUserClaims] = Depends(get_current_user_or_none)
        ) -> Response:
    """Refresh the access token"""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    session_cookie_key, classic_cookie_key, domain, secure, samesite = cookie_params(request)
    idp: ArxivOidcIdpClient = request.app.extra["idp"]
    new_claims = idp.refresh_access_token(current_user)
    #if current_user.tapir_cookie:
    #    new_claims.set_tapir_cookie(current_user.tapir_cookie)
    next_page = request.query_params.get('next_page', request.query_params.get('next', '/'))
    response = make_cookie_response(request, new_claims, next_page)
    return response


class RefreshedTokens(BaseModel):
    session: str
    classic: str
    domain: str
    max_age: int
    secure: bool
    samesite: str

@router.post('/refresh')
async def refresh_tokens(request: Request) -> Response:
    body = await request.body()
    session = body.get('session')
    if not session:
        logger.debug(f"There is no cookie.")

    try:
        tokens, jwt_payload = ArxivUserClaims.unpack_token(session)
    except ValueError:
        logger.error("The token is bad.")
        return None
    idp: ArxivOidcIdpClient = request.app.extra["idp"]
    user = idp.refresh_access_token(tokens)
    secret = request.app.extra['JWT_SECRET']

    content = RefreshedTokens(
        session = user.encode_jwt_token(secret),
        classic = body.get('classic'),
    )
    classic_cookie = body.gep('classic')
    response = make_cookie_response(request, user, classic_cookie, '', content=content)
    return response



@router.post('/logout')
@router.get('/logout')
async def logout(request: Request,
                 _db=Depends(get_db),
                 current_user: Optional[ArxivUserClaims] = Depends(get_current_user_or_none)) -> Response:
    """Log out of arXiv."""
    default_next_page = request.app.extra['ARXIV_URL_HOME']
    next_page = request.query_params.get('next_page', request.query_params.get('next', default_next_page))
    session_cookie_key, classic_cookie_key, domain, secure, samesite = cookie_params(request)

    classic_cookie = request.cookies.get(classic_cookie_key)

    logged_out = True
    if current_user is not None:
        logger.debug('Request to log out, then redirect to %s', next_page)
        idp: ArxivOidcIdpClient = request.app.extra["idp"]
        logged_out = idp.logout_user(current_user)

    if logged_out:
        response = make_cookie_response(request, None, "", next_page)

        if classic_cookie:
            try:
                legacy_invalidate(classic_cookie)
            except UnknownSession:
                # Trying to log out and there is no such session. What a happy coincidence
                logger.error("Tapir session has been gone")
                pass
            except Exception as exc:
                logger.error("Invalidating legacy session failed.", exc_info=exc)
                pass

        return response
    return RedirectResponse(next_page)



@router.post('/logout-callback')
async def logout(request: Request) -> Response:
    body = await request.body()
    logger.info("logout-callback body: %s", json.dumps(body))
    return Response(status_code=status.HTTP_200_OK)



@router.get('/token-names')
async def get_token_names(request: Request) -> JSONResponse:
    session_cookie_key, classic_cookie_key, _domain, _secure, _samesite = cookie_params(request)
    return {
        "session": session_cookie_key,
        "classic": classic_cookie_key
    }


@router.get('/check-db')
async def check_db(request: Request,
                   db: Session = Depends(get_db)) -> JSONResponse:
    from arxiv.db.models import TapirCountry
    count = db.query(func.count(TapirCountry.digraph)).scalar()
    return {"count": count}


def make_cookie_response(request: Request, user_claims: Optional[ArxivUserClaims],
                         tapir_cookie: str, next_page: str, content: Optional[Any] = None) -> Response:

    session_cookie_key, classic_cookie_key, domain, secure, samesite = cookie_params(request)
    session_duration = int(request.app.extra.get('SESSION_DURATION', '36000'))

    response: Response
    if (next_page):
        response = RedirectResponse(url=next_page, status_code=status.HTTP_303_SEE_OTHER)
    elif content:
        response = JSONResponse(content=content, status_code=status.HTTP_200_OK)
    else:
        response = Response(status_code=status.HTTP_200_OK)

    if user_claims:
        secret = request.app.extra['JWT_SECRET']
        token = user_claims.encode_jwt_token(secret)
        logger.debug('%s=%s',session_cookie_key, token)
        response.set_cookie(session_cookie_key, token, max_age=session_duration,
                            domain=domain, path="/", secure=secure, samesite=samesite)
    else:
        response.set_cookie(session_cookie_key, "", max_age=0,
                            domain=domain, path="/", secure=secure, samesite=samesite)

    if tapir_cookie:
        logger.debug('%s=%s',classic_cookie_key, tapir_cookie)
        response.set_cookie(classic_cookie_key, tapir_cookie, max_age=session_duration,
                            domain=domain, path="/", secure=secure, samesite=samesite)
    else:
        logger.debug('%s=<EMPTY>',classic_cookie_key)
        response.set_cookie(classic_cookie_key, '', max_age=0,
                            domain=domain, path="/", secure=secure, samesite=samesite)
    return response
