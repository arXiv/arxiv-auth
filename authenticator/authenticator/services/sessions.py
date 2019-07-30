"""
Provide service API for distributed sessions.

This module maps modules and functions required by the accounts service to
corresponding objects in the :mod:`arxiv.users` package.
"""

from arxiv.users.auth import exceptions
from arxiv.users.auth.sessions import SessionStore

InvalidToken = exceptions.InvalidToken
ExpiredToken = exceptions.ExpiredToken
UnknownSession = exceptions.UnknownSession

# init_app = sessions.store.init_app
# load = partial(sessions.store.load, decode=False)
# load_by_id = partial(sessions.store.load_by_id, decode=False)
