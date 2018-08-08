"""
Provide service API for distributed sessions.

This module maps modules and functions required by the accounts service to
corresponding objects in the :mod:`arxiv.users` package.
"""

from arxiv.users.auth import sessions, exceptions

init_app = sessions.store.init_app
create = sessions.store.create
generate_cookie = sessions.store.generate_cookie
invalidate = sessions.store.invalidate
invalidate_by_id = sessions.store.invalidate_by_id
delete = sessions.store.delete
load = sessions.store.load
