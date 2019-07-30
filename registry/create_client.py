"""
Script for creating a new user. For dev/test purposes only.

.. warning: DO NOT USE THIS ON A PRODUCTION DATABASE.

"""

import os
import sys
from typing import Tuple
from unittest import TestCase
from flask import Flask
import hashlib

from typing import List
import random
from datetime import datetime
from pytz import timezone, UTC
import click

from authlib.common.security import generate_token

from arxiv import taxonomy
from arxiv.users import domain

from registry.factory import create_web_app
from registry.services import datastore

EASTERN = timezone('US/Eastern')

DEFAULT_SCOPES = " ".join(([
    "public:read",
    "submission:create",
    "submission:update",
    "submission:read",
    "upload:create",
    "upload:update",
    "upload:read",
    "upload:read_logs",
]))


@click.command()
@click.option('--name', prompt='Brief client name')
@click.option('--url', prompt='Info URL for the client')
@click.option('--description', prompt='What is it')
@click.option('--scopes', prompt='Space-delimited authorized scopes',
              default=DEFAULT_SCOPES)
@click.option('--redirect_uri', prompt='Redirect URI')
def create_client(name: str, url: str, description: str, scopes: str,
                  redirect_uri: str) -> None:
    """Create a new client. For dev/test purposes only."""
    app = create_web_app()
    with app.app_context():
        datastore.create_all()

        with datastore.util.transaction() as session:
            db_client = datastore.models.DBClient(
                name=name,
                url=url,
                description=description,
                redirect_uri=redirect_uri
            )
            secret = generate_token(48)
            hashed = hashlib.sha256(secret.encode('utf-8')).hexdigest()
            db_cred = datastore.models.DBClientCredential(client=db_client,
                                                          client_secret=hashed)
            db_scopes = [
                datastore.models.DBClientAuthorization(
                    client=db_client, authorized=datetime.now(), scope=scope
                ) for scope in scopes.split()
            ]
            db_grant_type = datastore.models.DBClientGrantType(
                client=db_client,
                grant_type='client_credentials',
                authorized=datetime.now()
            )
            db_grant_type = datastore.models.DBClientGrantType(
                client=db_client,
                grant_type='authorization_code',
                authorized=datetime.now()
            )

            session.add(db_client)
            session.add(db_cred)
            session.add(db_grant_type)
            for db_scope in db_scopes:
                session.add(db_scope)

            session.commit()
        click.echo(f'Created client {name} with ID {db_client.client_id}'
                   f' and secret {secret}')


if __name__ == '__main__':
    create_client()
