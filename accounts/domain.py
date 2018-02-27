"""Defines the core data structures for the arxiv-accounts service."""

from typing import Any, Optional, Type, NamedTuple, List


class UserData(NamedTuple):
    """Data used to instantiate a user session."""

    user_id: int
    start_time: int
    end_time: int
    last_reissue: int

    # Tracking information.
    ip_address: str
    remote_host: str

    # For distributed session.
    user_name: str
    user_email: str
    scopes: List[str]

    # Consider for later:
    #  localization (preferred language)
    #  preferences for sharing contact info


class SessionData(NamedTuple):
    """Data returned by the session store upon successful creation."""

    session_id: str
    data: str

class SessionCreationFailed(RuntimeError):
    """Failed to create a session in the distributed session store."""    

class SessionDeletionFailed(RuntimeError):
    """Failed to delete a session in the session store."""
    