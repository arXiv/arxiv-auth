"""
Provide service API for legacy sessions.

This maps modules and functions required by the accounts service to
corresponding objects in the :mod:`arxiv.users.legacy` module.
"""
from functools import partial
from arxiv.base.globals import get_application_config as get_config
from arxiv.users import legacy

init_app = legacy.util.init_app
create_all = legacy.util.create_all
transaction = legacy.util.transaction
models = legacy.models
drop_all = legacy.util.drop_all
exceptions = legacy.exceptions

create = partial(legacy.sessions.create,
                 session_hash=get_config().get('CLASSIC_SESSION_HASH'))
invalidate = partial(legacy.sessions.invalidate,
                     session_hash=get_config().get('CLASSIC_SESSION_HASH'))
load = partial(legacy.sessions.load,
               session_hash=get_config().get('CLASSIC_SESSION_HASH'))
