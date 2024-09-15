"""Contains route information."""
from logging import getLogger
from fastapi import Request, HTTPException, status

import jwt
import jwcrypto
import jwcrypto.jwt

from arxiv.auth.user_claims import ArxivUserClaims
from sqlalchemy.orm import sessionmaker

ALGORITHM = "HS256"

def get_current_user_or_none(request: Request) -> ArxivUserClaims | None:
    logger = getLogger(__name__)
    session_cookie_key = request.app.extra['AUTH_SESSION_COOKIE_NAME']
    token = request.cookies.get(session_cookie_key)
    if not token:
        logger.debug(f"There is no cookie '{session_cookie_key}'")
        return None
    secret = request.app.extra['JWT_SECRET']
    if not secret:
        logger.error("The app is misconfigured or no JWT secret has been set")
        return None

    try:
        tokens, jwt_payload = ArxivUserClaims.unpack_token(token)
    except ValueError:
        logger.error("The token is bad.")
        return None

    try:
        claims = ArxivUserClaims.decode_jwt_payload(tokens, jwt_payload, secret)

    except jwcrypto.jwt.JWTExpired:
        # normal course of token expiring
        return None

    except jwcrypto.jwt.JWTInvalidClaimFormat:
        logger.warning(f"Chowed cookie '{token}'")
        return None

    except jwt.ExpiredSignatureError:
        # normal course of token expiring
        return None

    except jwt.DecodeError:
        logger.warning(f"Chowed cookie '{token}'")
        return None

    except Exception as exc:
        logger.warning(f"token {token} is wrong?", exc_info=exc)
        return None

    if not claims:
        logger.info(f"unpacking token {token} failed")
        return None
    return claims


def get_current_user(request: Request) -> ArxivUserClaims | None:
    user = get_current_user_or_none(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


SessionLocal = sessionmaker(autocommit=False, autoflush=False)
def get_db():
    """Dependency for fastapi routes"""
    from arxiv.db import _classic_engine
    db = SessionLocal(bind=_classic_engine)
    try:
        yield db
        if db.new or db.dirty or db.deleted:
            db.commit()
    except Exception as e:
        logger = getLogger(__name__)
        logger.warning(f'Commit failed, rolling back', exc_info=1)
        db.rollback()
        raise
    finally:
        db.close()
