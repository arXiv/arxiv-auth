"""
Provide service API for distributed sessions.

This module maps modules and functions required by the accounts service to
corresponding objects in the :mod:`arxiv.users` package.
"""

from arxiv.users.auth import sessions, exceptions
from arxiv.users.auth.sessions import SessionStore
# init_app = sessions.store.init_app
# create = sessions.store.create
# generate_cookie = sessions.store.generate_cookie
# delete_by_id = sessions.store.delete_by_id
# delete = sessions.store.delete
# load = sessions.store.load
