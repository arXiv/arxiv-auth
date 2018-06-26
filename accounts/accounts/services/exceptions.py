"""Provides exceptions occurring with external services."""


class SessionCreationFailed(RuntimeError):
    """Failed to create a session in the session store."""


class SessionDeletionFailed(RuntimeError):
    """Failed to delete a session in the session store."""


class SessionUnknown(RuntimeError):
    """Failed to locate a session in the session store."""
