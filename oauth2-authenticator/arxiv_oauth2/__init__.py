"""Contains route information."""
from logging import getLogger
from fastapi import Request, HTTPException, status

import jwt
import jwcrypto
import jwcrypto.jwt

from arxiv.auth.user_claims import ArxivUserClaims
from arxiv.db import SessionLocal

ALGORITHM = "HS256"

def get_current_user(request: Request) -> ArxivUserClaims | None:
    logger = getLogger(__name__)
    session_cookie_key = request.app.extra['AUTH_SESSION_COOKIE_NAME']
    token = request.cookies.get(session_cookie_key)
    if not token:
        logger.debug(f"There is no cookie '{session_cookie_key}'")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    secret = request.app.extra['JWT_SECRET']
    if not secret:
        logger.error("The app is misconfigured or no JWT secret has been set")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        claims = ArxivUserClaims.decode_jwt_token(token, secret)
    except jwcrypto.jwt.JWTExpired:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except jwcrypto.jwt.JWTInvalidClaimFormat:
        logger.warning(f"Chowed cookie '{token}'")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except jwt.DecodeError:
        logger.warning(f"Chowed cookie '{token}'")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except Exception as exc:
        logger.warning(f"token {token} is wrong?", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if not claims:
        logger.info(f"unpacking token {token} failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return claims


def get_db():
    """Dependency for fastapi routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

