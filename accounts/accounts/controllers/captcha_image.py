"""Provides the captcha image controller."""

from typing import Tuple
from werkzeug import MultiDict
from werkzeug.exceptions import BadRequest
from arxiv.users import domain
from accounts import stateless_captcha

ResponseData = Tuple[dict, int, dict]


def get(token: str, secret: str, ip_address: str) -> ResponseData:
    """Provide the image for stateless captcha."""
    if not token:
        raise BadRequest('Captcha token is required for this endpoint')
    try:
        image = stateless_captcha.render(token, secret, ip_address)
    except stateless_captcha.InvalidCaptchaToken as e:
        raise BadRequest('Invalid or expired captcha token') from e
    return {'image': image, 'mimetype': 'image/png'}
