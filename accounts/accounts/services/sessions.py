"""
Provide service API for distributed sessions.

This module maps modules and functions required by the accounts service to
corresponding objects in the :mod:`arxiv.users` package.
"""

from arxiv.users.auth import sessions, exceptions
from arxiv.users.auth.sessions import SessionStore