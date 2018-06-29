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
"""

import random
import io
from datetime import datetime, timedelta
import dateutil.parser
import string
import jwt
from captcha.image import ImageCaptcha


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
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=N))


def _secret(secret: str, ip_address) -> str:
    """Generate an encryption secret for the captha token."""
    return ':'.join([secret, ip_address])


def unpack(token: str, secret: str, ip_address: str) -> str:
    """Unpack a captcha token, and get the target value."""
    try:
        claims = jwt.decode(token.encode('ascii'),
                            _secret(secret, ip_address))
    except jwt.exceptions.DecodeError:
        raise InvalidCaptchaToken('Could not decode token')
    try:
        if dateutil.parser.parse(claims['expires']) <= datetime.now():
            raise InvalidCaptchaToken('Expired token')
        return claims['value']
    except (KeyError, ValueError) as e:
        raise InvalidCaptchaToken('Malformed content') from e


def new(secret: str, ip_address: str, expires: int = 300) -> str:
    """Generate a captcha token."""
    claims = {
        'value': _generate_random_string(),
        'expires': (datetime.now() + timedelta(seconds=300)).isoformat()
    }
    return jwt.encode(claims, _secret(secret, ip_address)).decode('ascii')


def render(token: str, secret: str, ip_address: str) -> io.BytesIO:
    """Render a captcha image using the value in a captcha token."""
    value = unpack(token, secret, ip_address)
    image = ImageCaptcha()  # TODO: look at font options.
    return image.generate(value)


def check(token: str, value: str, secret: str, ip_address: str) -> None:
    """
    Evaluate whether a value matches a captcha token.

    Raises
    ------
    :class:`InvalidCaptchaValue`

    """
    if value != unpack(token, secret, ip_address):
        raise InvalidCaptchaValue('Incorrect value for this captcha')
