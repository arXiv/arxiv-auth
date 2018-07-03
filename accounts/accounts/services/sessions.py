"""
Provide service API for distributed sessions.

This maps modules and functions required by the accounts service to
corresponding objects in the :mod:`arxiv.users` package.
"""

from arxiv.users.auth import sessions, exceptions

init_app = sessions.store.init_app
create = sessions.store.create
invalidate = sessions.store.invalidate
load = sessions.store.load
