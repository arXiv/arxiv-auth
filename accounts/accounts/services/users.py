"""
Provide service API for legacy user data.

This maps modules and functions required by the accounts service to
corresponding objects in the :mod:`arxiv.users.legacy` module.
"""

from arxiv.users import legacy

init_app = legacy.util.init_app
transaction = legacy.util.transaction
models = legacy.models
drop_all = legacy.util.drop_all
exceptions = legacy.exceptions
authenticate = legacy.authenticate.authenticate
get_user_by_id = legacy.authenticate.get_user_by_id

register = legacy.register.register
username_exists = legacy.register.username_exists
email_exists = legacy.register.email_exists


def create_all() -> None:
    """Initialize the legacy database."""
    legacy.util.create_all()
    with legacy.util.transaction() as session:
        data = session.query(legacy.models.DBPolicyClass).all()
        if data:
            return

        for datum in legacy.models.DBPolicyClass.POLICY_CLASSES:
            session.add(legacy.models.DBPolicyClass(**datum))
