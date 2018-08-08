"""
Provide service API for distributed sessions.

This module maps modules and functions required by the accounts service to
corresponding objects in the :mod:`arxiv.users` package.
"""

from arxiv.users.auth import sessions, exceptions

init_app = sessions.store.init_app
load = sessions.store.load
load_by_id = sessions.store.load_by_id
