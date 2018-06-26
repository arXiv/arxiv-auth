"""Defines the core data structures for the arxiv-accounts service."""

from typing import Any, Optional, Type, NamedTuple, List
from datetime import datetime
from arxiv import taxonomy
import pycountry
from arxiv import users


class UserRegistration(NamedTuple):
    """Represents a request to register a new user."""

    username: str
    password: str
    email: str
    name: users.UserFullName
    profile: users.UserProfile
