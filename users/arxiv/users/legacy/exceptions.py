"""Exceptions."""


class AuthenticationFailed(RuntimeError):
    """Failed to authenticate user with provided credentials."""


class NoSuchUser(RuntimeError):
    """User does not exist."""


class PasswordAuthenticationFailed(RuntimeError):
    """Password is not correct."""


class SessionCreationFailed(RuntimeError):
    """Failed to create a session in the session store."""


class SessionDeletionFailed(RuntimeError):
    """Failed to delete a session in the session store."""


class SessionUnknown(RuntimeError):
    """Failed to locate a session in the session store."""


class SessionExpired(RuntimeError):
    """User's session has expired."""
