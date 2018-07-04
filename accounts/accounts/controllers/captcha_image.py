"""Provides the captcha image controller."""

from typing import Tuple
from werkzeug import MultiDict
from werkzeug.exceptions import BadRequest
from arxiv.users import domain
from arxiv import status
from accounts import stateless_captcha

ResponseData = Tuple[dict, int, dict]


def get(token: str, secret: str, ip_address: str) -> ResponseData:
    """Provide the image for stateless captcha."""
    if not token:
        raise BadRequest('Token is required for this endpoint')  # type: ignore
    try:
        image = stateless_captcha.render(token, secret, ip_address)
    except stateless_captcha.InvalidCaptchaToken as e:
        raise BadRequest('Invalid or expired token') from e  # type: ignore
    return {'image': image, 'mimetype': 'image/png'}, status.HTTP_200_OK, {}
