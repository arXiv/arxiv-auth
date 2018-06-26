"""Map user service API onto legacy database."""

from arxiv.users import legacy

init_app = legacy.util.init_app
create_all = legacy.util.create_all
transaction = legacy.util.transaction
models = legacy.models
drop_all = legacy.util.drop_all
exceptions = legacy.exceptions
authenticate = legacy.authenticate.authenticate
