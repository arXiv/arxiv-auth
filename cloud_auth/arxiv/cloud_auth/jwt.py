from typing import Optional, Literal
import jwt
from .domain import Auth

def decode(token: str, secret: str):
    """Decode an auth token to access session information."""
    data = dict(jwt.decode(token, secret, algorithms=["HS256"]))
    return data


def encode(user: Auth, secret: str) -> str:
    """Encode a auth token"""
    return jwt.encode(vars(user), secret)


def user_jwt(user_id: int, secret: str) -> str:
    """For use in testing to make a jwt."""
    return encode(
        Auth(
            user_id=user_id, session_id="fakesessionid",
            nonce="peaceout", expires="0"
        ),
        secret
    )
