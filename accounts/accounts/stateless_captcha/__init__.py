"""
Stateless captcha.

This module provides a captcha that does not require storing anything.

When the user visits a form view for which captcha is required, a new
captcha token can be generated using the :func:`.new` function in this module.
The token contains the challenge answer, as well as an expiration. The token is
encrypted using a server-side secret and the IP address of the client.

The captcha token can be used to generate an image that depicts the captcha
challenge, using the :func:`.render` function in this module.

When the user enters an answer to the challenge, the answer can be checked
against the token using the :func:`.check` function. If the token is expired,
or cannot be decrypted for some reason (e.g. forgery, change of IP address),
an :class:`InvalidCaptchaToken` exception is raised. If the token can be
interpreted but the value is incorrect, an :class:`InvalidCaptchaValue`
exception is raised.

This was implemented as a stand-alone module in case we want to generalize it
for use elsewhere.
"""

import random
import io
from typing import Dict, Mapping, Any, Optional
from datetime import datetime, timedelta
from pytz import timezone, UTC
import dateutil.parser
import string
import jwt
from captcha.image import ImageCaptcha

from arxiv.base import logging

EASTERN = timezone('US/Eastern')
logger = logging.getLogger(__name__)


class InvalidCaptchaToken(ValueError):
    """A token was passed that is either expired or corrupted."""


class InvalidCaptchaValue(ValueError):
    """The passed value did not match the associated captcha token."""


def _generate_random_string(N: int = 6) -> str:
    """
    Generate some random characers to use in the captcha.

    Parameters
    ----------
    N : int
        Number of characters to generate.

    Returns
    -------
    str
        A pseudo-random sequence of lowercase letters and numbers, ``N``
        characters in length.

    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))


def _secret(secret: str, ip_address: str) -> str:
    """Generate an encryption secret for the captha token."""
    return ':'.join([secret, ip_address])


def unpack(token: str, secret: str, ip_address: str) -> str:
    """
    Unpack a captcha token, and get the target value.

    Parameters
    ----------
    token : str
        A captcha token (see :func:`new`).
    secret : str
        The captcha secret used to generate the token.
    ip_address : str
        The client IP address used to generate the token.

    Returns
    -------
    str
        The captcha challenge (i.e. the text that the user is asked to enter).

    Raises
    ------
    :class:`InvalidCaptchaToken`
        Raised if the token is malformed, expired, or the IP address does not
        match the one used to generate the token.

    """
    logger.debug('Unpack captcha token, %s', token)
    try:
        claims: Mapping[str, Any] = jwt.decode(token,
                                               _secret(secret, ip_address),
                                               algorithms=['HS256'])
        logger.debug('Unpacked captcha token: %s', claims)
    except jwt.exceptions.DecodeError:  # type: ignore
        raise InvalidCaptchaToken('Could not decode token')
    try:
        now = datetime.now(tz=UTC)
        if dateutil.parser.parse(claims['expires']) <= now:
            logger.debug('captcha token expired: %s', claims['expires'])
            raise InvalidCaptchaToken('Expired token')
        value: str = claims['value']
        return value
    except (KeyError, ValueError) as e:
        logger.debug('captcha token invalid: %s', e)
        raise InvalidCaptchaToken('Malformed content') from e


def new(secret: str, ip_address: str, expires: int = 300) -> str:
    """
    Generate a captcha token.

    Parameters
    ----------
    secret : str
        Used to encrypt the captcha challenge.
    ip_address : str
        The client IP address, also used to encrypt the token.
    expires : int
        Number of seconds for which the token is valid. Default is 300 (5
        minutes).

    Returns
    -------
    str
        A captcha token, which contains a captcha challenge and expiration.

    """
    claims = {
        'value': _generate_random_string(),
        'expires': (datetime.now(tz=UTC) + timedelta(seconds=300)).isoformat()
    }
    return jwt.encode(claims, _secret(secret, ip_address))


def render(token: str, secret: str, ip_address: str,
           font: Optional[str] = None) -> io.BytesIO:
    """
    Render a captcha image using the value in a captcha token.

    Parameters
    ----------
    token : str
        A captcha token (see :func:`new`).
    secret : str
        The captcha secret used to generate the token.
    ip_address : str
        The client IP address used to generate the token.

    Returns
    -------
    :class:`io.BytesIO`
        PNG image data.

    Raises
    ------
    :class:`InvalidCaptchaToken`
        Raised if the token is malformed, expired, or the IP address does not
        match the one used to generate the token.

    """
    value = unpack(token, secret, ip_address)
    if font is not None:
        image = ImageCaptcha(fonts=[font], width=400)
    else:
        image = ImageCaptcha()
    data: io.BytesIO = image.generate(value)
    return data


def check(token: str, value: str, secret: str, ip_address: str) -> None:
    """
    Evaluate whether a value matches a captcha token.

    Parameters
    ----------
    token : str
        A captcha token (see :func:`new`).
    value : str
        The value of the captcha challenge (i.e. the text that the user is
        asked to enter).
    secret : str
        The captcha secret used to generate the token.
    ip_address : str
        The client IP address used to generate the token.

    Raises
    ------
    :class:`InvalidCaptchaValue`
        If the passed ``value`` does not match the challenge contained in the
        token, this exception is raised.
    :class:`InvalidCaptchaToken`
        Raised if the token is malformed, expired, or the IP address does not
        match the one used to generate the token.

    """
    target = unpack(token, secret, ip_address)
    logger.debug('target: %s, value: %s', target, value)
    if value != target:
        logger.debug('incorrect value for this captcha')
        raise InvalidCaptchaValue('Incorrect value for this captcha')
