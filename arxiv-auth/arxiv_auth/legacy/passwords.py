"""Passwords from legacy."""

import secrets
from base64 import b64encode, b64decode
import hashlib

from arxiv.base import logging

from .exceptions import PasswordAuthenticationFailed

logger = logging.getLogger(__name__)

def _hash_salt_and_password(salt: bytes, password: str) -> bytes:
    return hashlib.sha1(salt + b'-' + password.encode('ascii')).digest()


def hash_password(password: str) -> str:
    """Generate a secure hash of a password.

    The password must be ascii.
    """
    salt = secrets.token_bytes(4)
    hashed = _hash_salt_and_password(salt, password)
    return b64encode(salt + hashed).decode('ascii')


def check_password(password: str, encrypted: bytes, storage_type=2):
    """Check a password against an encrypted hash."""
    if storage_type not in [0,1,2,3]:
        raise PasswordAuthenticationFailed('Invalid storage_type')

    try:
        password.encode('ascii')
    except UnicodeEncodeError:
        raise PasswordAuthenticationFailed('Password not ascii')

    if storage_type in [0,3]:
        raise PasswordAuthenticationFailed(f'storage_type {storage_type} deprecated')
    elif storage_type == 1:
        salt,hash = encrypted.split(b'-')
        newhash = hashlib.md5(f"{salt}-{password}".encode('ascii')).digest()
        if newhash !=hash:
            raise PasswordAuthenticationFailed('Incorrect password')
        else:
            return True
    elif storage_type == 2:
        decoded = b64decode(encrypted)
        salt = decoded[:4]
        enc_hashed = decoded[4:]
        pass_hashed = _hash_salt_and_password(salt, password)
        if pass_hashed != enc_hashed:
            raise PasswordAuthenticationFailed('Incorrect password')
        else:
            return True
    else:
        raise PasswordAuthenticationFailed('unknown storage_type')


def is_ascii(string):
    """Returns true if the string is only ascii chars."""
    try:
        string.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False
