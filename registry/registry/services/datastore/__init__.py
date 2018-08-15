"""Database integration for persisting API client information."""

from typing import List, Tuple, Optional
from . import util, models
from ... import domain


class NoSuchClient(RuntimeError):
    """A client was requested that does not exist."""


class NoSuchAuthorization(RuntimeError):
    """A non-existant :class:`domain.ClientAuthorization` was requested."""


class NoSuchGrantType(RuntimeError):
    """A non-existant :class:`domain.ClientGrantType` was requested."""


class NoSuchAuthCode(RuntimeError):
    """A non-existant :class:`domain.AuthorizationCode` was requested."""


init_app = util.init_app
create_all = util.create_all
drop_all = util.drop_all


def save_client(
        client: domain.Client,
        cred: Optional[domain.ClientCredential] = None,
        auths: Optional[List[domain.ClientAuthorization]] = None,
        grant_types: Optional[List[domain.ClientGrantType]] = None) -> str:
    """
    Persist a :class:`domain.Client` and (optionally) related data.

    Parameters
    ----------
    client : :class:`domain.Client`
    cred : :class:`domain.ClientCredential` or None
    auths : list or None
        Items are :class:`domain.ClientAuthorization` instances.
    grant_types : list or None
        Items are :class:`domain.ClientGrantType` instances.

    """
    with util.transaction() as dbsession:
        if client.client_id:
            db_client = _load_dbclient(client.client_id, dbsession)
            db_client.owner_id = client.owner_id
            db_client.name = client.name
            db_client.url = client.url
            db_client.description = client.description
            db_client.redirect_uri = client.redirect_uri
        else:
            db_client = models.DBClient(
                owner_id=client.owner_id,
                name=client.name,
                url=client.url,
                description=client.description,
                redirect_uri=client.redirect_uri
            )
        dbsession.add(db_client)
        if cred:
            set_credential(cred, db_client=db_client, commit=False)
        if auths:
            update_authorizations(auths, db_client=db_client, commit=False)
        if grant_types:
            update_grant_types(grant_types, db_client=db_client, commit=False)
    return str(db_client.client_id)


def set_credential(cred: domain.ClientCredential,
                   client_id: Optional[str] = None,
                   db_client: Optional[models.DBClient] = None,
                   commit: bool = True) -> None:
    with util.transaction(commit) as dbsession:
        if db_client is None:
            db_client = _load_dbclient(client_id, dbsession)
        if db_client.credential:
            db_client.credential.client_secret = cred.client_secret
            dbsession.add(db_client)
        else:
            dbsession.add(models.DBClientCredential(
                client=db_client,
                client_secret=cred.client_secret
            ))


def update_authorizations(auths: List[domain.ClientAuthorization],
                          client_id: Optional[str] = None,
                          db_client: Optional[models.DBClient] = None,
                          commit: bool = True) -> None:
    with util.transaction(commit) as dbsession:
        if db_client is None:
            db_client = _load_dbclient(client_id, dbsession)
        auths_to_keep = set([auth.authorization_id for auth in auths
                             if auth.authorization_id])
        extant_auths = {str(auth.authorization_id): auth
                        for auth in db_client.authorizations}
        # Remove auths from the datastore that are not included.
        for auth_id in set(extant_auths.keys()) - auths_to_keep:
            dbsession.delete(extant_auths[auth_id])

        # Add or update auths in the datastore.
        for auth in auths:
            # Does not yet exist in the datastore.
            if auth.authorization_id is None:
                dbsession.add(
                    models.DBClientAuthorization(
                        client=db_client,
                        scope=auth.scope,
                        requested=auth.requested,
                        authorized=auth.authorized
                    )
                )
            # Update an existing auth.
            elif auth.authorization_id in extant_auths:
                db_auth = extant_auths[auth.authorization_id]
                db_auth.scope = auth.scope
                db_auth.requested = auth.requested
                db_auth.authorized = auth.authorized
                dbsession.add(db_auth)
            else:
                raise NoSuchAuthorization(
                    f'No auth {auth.authorization_id} for client'
                )


def update_grant_types(grant_types: List[domain.ClientGrantType],
                       client_id: Optional[str] = None,
                       db_client: Optional[models.DBClient] = None,
                       commit: bool = True) -> None:
    with util.transaction(commit) as dbsession:
        if db_client is None:
            db_client = _load_dbclient(client_id, dbsession)
        gtypes_to_keep = set([g.grant_type_id for g in grant_types
                              if g.grant_type_id])
        extant_gtypes = {str(g.grant_type_id): g
                         for g in db_client.grant_types}
        # Remove grant_types from the datastore that are not included.
        for gtype_id in set(extant_gtypes.keys()) - gtypes_to_keep:
            dbsession.delete(extant_gtypes[gtype_id])

        # Add or update grant_types in the datastore.
        for gtype in grant_types:
            # Does not yet exist in the datastore.
            if gtype.grant_type_id is None:
                dbsession.add(
                    models.DBClientGrantType(
                        client=db_client,
                        grant_type=gtype.grant_type,
                        requested=gtype.requested,
                        authorized=gtype.authorized
                    )
                )
            # Update an existing auth.
            elif gtype.grant_type_id in extant_gtypes:
                db_grant_type = extant_gtypes[gtype.grant_type_id]
                db_grant_type.grant_type = gtype.grant_type
                db_grant_type.requested = gtype.requested
                db_grant_type.authorized = gtype.authorized
                dbsession.add(db_grant_type)
            else:
                raise NoSuchGrantType(
                    f'No grant type {gtype.grant_type_id} for client'
                )


def load_client(client_id: str) -> Tuple[domain.Client,
                                         Optional[domain.ClientCredential],
                                         List[domain.ClientAuthorization],
                                         List[domain.ClientGrantType]]:
    """Load a :class:`.Client` from the datastore."""
    with util.transaction() as dbsession:
        db_client = _load_dbclient(client_id, dbsession)
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
        if db_client.credential:
            cred = domain.ClientCredential(
                client_id=str(db_client.client_id),
                client_secret=str(db_client.credential.client_secret)
            )
        else:
            cred = None
        auths = [domain.ClientAuthorization(
            authorization_id=str(auth.authorization_id),
            client_id=str(db_client.client_id),
            scope=str(auth.scope),
            requested=auth.requested,
            authorized=auth.authorized
        ) for auth in db_client.authorizations]
        grant_types = [domain.ClientGrantType(
            grant_type_id=str(grant_type.grant_type_id),
            client_id=str(db_client.client_id),
            grant_type=str(grant_type.grant_type),
            requested=grant_type.requested,
            authorized=grant_type.authorized
        ) for grant_type in db_client.grant_types]
        return client, cred, auths, grant_types


def save_auth_code(code: domain.AuthorizationCode) -> None:
    """Save a new authorization code."""
    with util.transaction() as dbsession:
        db_code = models.DBAuthorizationCode(
            code=code.code,
            user_id=code.user_id,
            user_email=code.user_email,
            username=code.username,
            client_id=code.client_id,
            redirect_uri=code.redirect_uri,
            scope=code.scope,
            created=code.created,
            expires=code.expires
        )
        dbsession.add(db_code)


def delete_auth_code(code: str, client_id: int) -> None:
    """Delete an auth code from the database."""
    with util.transaction() as dbsession:
        db_code = _load_dbauthcode(code, client_id, dbsession)
        dbsession.delete(db_code)


def load_auth_code(code: str, client_id: int) -> domain.AuthorizationCode:
    """Load an authorization code for an API client."""
    with util.transaction() as dbsession:
        db_code = _load_dbauthcode(code, client_id, dbsession)

    return domain.AuthorizationCode(
        code=code,
        user_id=db_code.user_id,
        user_email=db_code.user_email,
        username=db_code.username,
        client_id=db_code.client_id,
        redirect_uri=db_code.redirect_uri,
        scope=db_code.scope,
        created=db_code.created,
        expires=db_code.expires
    )


def load_auth_code_by_user(code: str, user_id: str) \
        -> domain.AuthorizationCode:
    """Load an authorization code for an API client."""
    with util.transaction() as dbsession:
        db_code = dbsession.query(models.DBAuthorizationCode)\
            .filter(models.DBAuthorizationCode.code == code) \
            .filter(models.DBAuthorizationCode.user_id == user_id) \
            .first()
        if db_code is None:
            raise NoSuchAuthCode(f'Auth code {code} does not exist'
                                 f' for user {user_id}')

    return domain.AuthorizationCode(
        code=code,
        user_id=db_code.user_id,
        user_email=db_code.user_email,
        username=db_code.username,
        client_id=db_code.client_id,
        redirect_uri=db_code.redirect_uri,
        scope=db_code.scope,
        created=db_code.created,
        expires=db_code.expires
    )


def _load_dbauthcode(code: str, client_id: int, dbsession: util.Session) \
        -> None:
    db_code = dbsession.query(models.DBAuthorizationCode)\
        .filter(models.DBAuthorizationCode.code == code) \
        .filter(models.DBAuthorizationCode.client_id == client_id) \
        .first()
    if db_code is None:
        raise NoSuchAuthCode(f'Auth code {code} does not exist'
                             f' for client {client_id}')
    return db_code


def _load_dbclient(client_id: str, dbsession: util.Session) -> models.DBClient:
    db_client: models.DBClient = dbsession.query(models.DBClient) \
        .filter(models.DBClient.client_id == client_id) \
        .first()
    if db_client is None:
        raise NoSuchClient(f'Client {client_id} does not exist')
    return db_client
