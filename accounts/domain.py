from typing import Any, Optional, Type, NamedTuple, List


class UserData(NamedTuple):
    """Data used to instantiate a user session."""

    user_id: int
    start_time: int
    end_time: int
    last_reissue: int

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
    cookie_data: str
