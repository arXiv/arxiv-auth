"""Provide service API for legacy sessions."""

from arxiv.users import legacy

init_app = legacy.util.init_app
transaction = legacy.util.transaction
models = legacy.models
drop_all = legacy.util.drop_all
exceptions = legacy.exceptions
create = legacy.sessions.create
invalidate = legacy.sessions.invalidate
load = legacy.sessions.load


def create_all() -> None:
    """Initialize the legacy database."""
    legacy.util.create_all()
    with legacy.util.transaction() as session:
        data = session.query(legacy.models.DBPolicyClass).all()
        if data:
            return

        for datum in legacy.models.DBPolicyClass.POLICY_CLASSES:
            session.add(legacy.models.DBPolicyClass(**datum))
