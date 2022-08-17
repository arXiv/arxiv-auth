"""Provides functions for working with legacy session cookies.

The legacy cookie is 6 parts seperated with ':'.

The parts are:
1. session id
2. tapir_users.user_id
3. ip the session was started at
4. time issued at as unix epoch
5. 'capacilites'
6. b64 encoced sha1 hash of parts 1-5

In a way it is similar to a JWT where parts 1-5 are similar to the JWT
payload, though fixed in strucutre, and part 6 forms the signature.

Parts 1-5 are not b64 encoded.
"""

from typing import Tuple
from base64 import b64encode
import hashlib
from datetime import datetime, timedelta

from .exceptions import InvalidCookie
from . import util


def unpack(cookie: str) -> Tuple[str, str, str, datetime, datetime, str]:
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
    datetime
        The datetime when the session was created.
    datetime
        The datetime when the session expires.
    str
        Legacy user privilege level.

    Raises
    ------
    :class:`InvalidCookie`
        Raised if the cookie is detectably malformed or tampered with.

    """
    parts = cookie.split(':')
    if len(parts) < 5:
        raise InvalidCookie('Malformed cookie')

    session_id = parts[0]
    user_id = parts[1]
    ip = parts[2]
    issued_at = util.from_epoch(int(parts[3]))
    expires_at = issued_at + timedelta(seconds=util.get_session_duration())
    capabilities = parts[4]
    try:
        expected = pack(session_id, user_id, ip, issued_at, capabilities)
    except Exception as e:
        raise InvalidCookie('Invalid session cookie; problem while repacking') from e

    if expected == cookie:
        return session_id, user_id, ip, issued_at, expires_at, capabilities
    else:
        raise InvalidCookie('Invalid session cookie; not as expected')


def pack(session_id: str, user_id: str, ip: str, issued_at: datetime,
         capabilities: str) -> str:
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
    issued_at : datetime
        The UNIX time at which the session was initiated.
    capabilities : str
        This is essentially a user privilege level.

    Returns
    -------
    str
        Signed session cookie value.

    """
    session_hash = util.get_session_hash()
    value = ':'.join(map(str, [session_id, user_id, ip, util.epoch(issued_at),
                               capabilities]))
    to_sign = f'{value}-{session_hash}'.encode('utf-8')
    cookie_hash = b64encode(hashlib.sha1(to_sign).digest())
    return value + ':' + cookie_hash.decode('utf-8')[:-1]
