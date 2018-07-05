"""Provides functions for working with legacy session cookies."""

from typing import Tuple
from base64 import b64encode, b64decode
import hashlib

from .exceptions import InvalidCookie
from . import util


def unpack(cookie: str) -> Tuple[str, str, str, str]:
    """
    Unpack the legacy session cookie.

    Parameters
    ----------
    cookie : str
        The value of session cookie.

    Returns
    -------
    str
        The session ID associated with the cookie.
    str
        The user ID of the authenticated account.
    str
        The IP address of the client when the session was created.
    str
        Legacy user privilege level.

    Raises
    ------
    :class:`InvalidCookie`
        Raised if the cookie is detectably malformed or tampered with.

    """
    parts = cookie.split(':')
    payload: Tuple[str, str, str, str]
    payload = tuple(part for part in parts[:4])  # type: ignore

    try:
        expected_cookie = pack(*payload)
        assert expected_cookie == cookie
    except (TypeError, AssertionError) as e:
        raise InvalidCookie('Invalid session cookie; forged?') from e
    return payload


def pack(session_id: str, user_id: str, ip: str, capabilities: str) -> str:
    """
    Generate a value for the classic session cookie.

    Parameters
    ----------
    session_id : str
        The session ID associated with the cookie.
    user_id : str
        The user ID of the authenticated account.
    ip : str
        Client IP address.
    capabilities : str
        This is essentially a user privilege level.

    Returns
    -------
    str
        Signed session cookie value.

    """
    session_hash = util.get_session_hash()
    value = ':'.join(map(str, [session_id, user_id, ip, capabilities]))
    to_sign = f'{value}-{session_hash}'.encode('utf-8')
    cookie_hash = b64encode(hashlib.sha256(to_sign).digest())
    return value + ':' + cookie_hash.decode('utf-8')
