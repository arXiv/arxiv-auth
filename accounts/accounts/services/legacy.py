"""
Provide service API for legacy sessions.

This maps modules and functions required by the accounts service to
corresponding objects in the :mod:`arxiv.users.legacy` module.
"""
from functools import wraps
from arxiv.users import legacy

init_app = legacy.util.init_app
create_all = legacy.util.create_all
transaction = legacy.transaction
models = legacy.models
drop_all = legacy.util.drop_all
exceptions = legacy.exceptions
invalidate_by_id = legacy.sessions.invalidate_by_id
create = legacy.sessions.create
invalidate = legacy.sessions.invalidate
load = legacy.sessions.load
generate_cookie = legacy.sessions.generate_cookie
is_available = legacy.is_available
