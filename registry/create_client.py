"""
Script for creating a new user. For dev/test purposes only.

.. warning: DO NOT USE THIS ON A PRODUCTION DATABASE.

"""

import os
import sys
from typing import Tuple
from unittest import TestCase
from flask import Flask

from typing import List
import random
from datetime import datetime
from pytz import timezone
import click

from arxiv import taxonomy
from arxiv.users import domain

from registry.factory import create_web_app
from registry.services import datastore

EASTERN = timezone('US/Eastern')


@click.command()
@click.option('--name', prompt='Brief client name')
@click.option('--url', prompt='Info URL for the client')
@click.option('--description', prompt='What is it')
@click.option('--secret', prompt='Client secret')
@click.option('--scopes', prompt='Comma-delimited authorized scopes')
def create_client(name: str, url: str, description: str, secret: str,
                  scopes: str) -> None:
    """Create a new client. For dev/test purposes only."""
    app = create_web_app()
    with app.app_context():
        datastore.create_all()

    with datastore.util.transaction() as session:
        db_client = datastore.models.DBClient(
            name=name,
            url=url,
            description=description
        )
        db_cred = datastore.models.DBClientCredential(client=db_client,
                                                      client_secret=secret)
        db_scopes = [
            datastore.models.DBClientAuthorization(
                client=db_client, authorized=datetime.now(), scope=scope
            ) for scope in scopes.split(',')
        ]
        db_grant_type = datastore.models.DBClientGrantType(
            client=db_client,
            grant_type='client_credentials',
            authorized=datetime.now()
        )

        session.add(db_client)
        session.add(db_cred)
        session.add(db_grant_type)
        for db_scope in db_scopes:
            session.add(db_scope)

        session.commit()


if __name__ == '__main__':
    create_client()
