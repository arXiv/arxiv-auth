"""Database integration for persisting API client information."""

from typing import List, Tuple
from . import util, models
from ... import domain


class NoSuchClient(RuntimeError):
    """A client was requested that does not exist."""


def load_client(client_id: str) -> Tuple[domain.Client,
                                         domain.ClientCredential,
                                         List[domain.ClientAuthorization],
                                         List[domain.ClientGrantType]]:
    """Load a :class:`.Client` from the datastore."""
    with util.transaction() as dbsession:
        db_client: models.DBClient = dbsession.query(models.DBClient) \
            .filter(models.DBClient.client_id == client_id) \
            .first()
        if db_client is None:
            raise NoSuchClient(f'Client {client_id} does not exist')
        params = {
            "client_id": db_client.client_id,
            "owner_id": db_client.owner_id,
            "name": db_client.name,
            "url": db_client.url,
            "description": db_client.description,
            "redirect_uri": db_client.redirect_uri
        }
        client = domain.Client(**{k: str(v) if v is not None else None
                                  for k, v in params.items()})
        cred = domain.ClientCredential(
            client_id=str(db_client.client_id),
            client_secret=str(db_client.credential.client_secret)
        )
        auths = [domain.ClientAuthorization(
            client_id=str(db_client.client_id),
            scope=str(auth.scope),
            requested=auth.requested,
            authorized=auth.authorized
        ) for auth in db_client.authorizations]
        grant_types = [domain.ClientGrantType(
            client_id=str(db_client.client_id),
            grant_type=str(grant_type.grant_type),
            requested=grant_type.requested,
            authorized=grant_type.authorized
        ) for grant_type in db_client.grant_types]
        return client, cred, auths, grant_types


init_app = util.init_app
create_all = util.create_all
