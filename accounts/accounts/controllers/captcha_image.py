"""Provides the captcha image controller."""

from typing import Tuple, Optional
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import BadRequest
from arxiv_auth import domain
from arxiv import status
from accounts import stateless_captcha

ResponseData = Tuple[dict, int, dict]


def get(token: str, secret: str, ip_address: str,
        font: Optional[str] = None) -> ResponseData:
    """Provide the image for stateless captcha."""
    if not token:
        raise BadRequest('Token is required for this endpoint')  # type: ignore
    try:
        image = stateless_captcha.render(token, secret, ip_address, font=font)
    except stateless_captcha.InvalidCaptchaToken as e:
        raise BadRequest('Invalid or expired token') from e  # type: ignore
    return {'image': image, 'mimetype': 'image/png'}, status.HTTP_200_OK, {}
