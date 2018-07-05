"""Request controllers for the user accounts application."""

import uuid
from . import authentication, captcha_image, registration


def generate_tracking_cookie(ip_address: str) -> bytes:
    """Generate a tracking cookie value from a client IP address."""
    return f'{ip_address}.{uuid.uuid4()}'.encode('utf-8')
