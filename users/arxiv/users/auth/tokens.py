"""Functions for working with authn/z tokens on user/client requests."""

import jwt
from . import exceptions
from .. import domain


def encode(session: domain.Session, secret: str) -> str:
    """Encode session information as an encrypted JWT."""
    return jwt.encode(domain.to_dict(session), secret)


def decode(token: str, secret: str) -> domain.Session:
    """Decode an auth token to access session information."""
    try:
        data: dict = jwt.decode(token, secret, algorithms=['HS256'])
    except jwt.exceptions.DecodeError as e:
        raise exceptions.InvalidToken('Not a valid token') from e

    return domain.from_dict(domain.Session, data)
