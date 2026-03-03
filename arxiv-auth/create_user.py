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
from pytz import timezone, UTC
import click

from arxiv import taxonomy
from arxiv_auth.legacy import models, util, sessions, authenticate, exceptions
from arxiv_auth.legacy.password import hash_password
from arxiv_auth import domain

from accounts.factory import create_web_app
from accounts.services import legacy, users

EASTERN = timezone('US/Eastern')


def _random_category() -> Tuple[str, str]:
    category = random.choice(list(taxonomy.CATEGORIES.items()))
    archive = category[1]['in_archive']
    subject_class = category[0].split('.')[-1] if '.' in category[0] else ''
    return archive, subject_class


def _prob(P: int) -> bool:
    return random.randint(0, 100) < P


@click.command()
@click.option('--username', prompt='Your username')
@click.option('--email', prompt='Your email address')
@click.option('--password', prompt='Your password')
@click.option('--first-name', prompt='Your first name')
@click.option('--last-name', prompt='Your last name')
@click.option('--suffix-name', prompt='Your name suffix', default='')
@click.option('--affiliation', prompt='Your affiliation', default='FSU')
@click.option('--home-page', prompt='Your homepage',
              default='https://asdf.com')
def create_user(username: str, email: str, password: str,
                first_name: str, last_name: str, suffix_name: str = '',
                affiliation: str = 'FSU', home_page: str = 'https://asdf.com'):
    """Create a new user. For dev/test purposes only."""
    app = create_web_app()
    with app.app_context():
        legacy.create_all()
        users.create_all()

        with util.transaction() as session:
            ip_addr = '127.0.0.1'
            joined_date = util.epoch(datetime.now().replace(tzinfo=EASTERN))
            db_user = models.DBUser(
                first_name=first_name,
                last_name=last_name,
                suffix_name=suffix_name,
                share_first_name=1,
                share_last_name=1,
                email=email,
                flag_approved=1,
                flag_deleted=0,
                flag_banned=0,
                flag_edit_users=0,
                flag_edit_system=0,
                flag_email_verified=1,
                share_email=8,
                email_bouncing=0,
                policy_class=2,  # Public user. TODO: consider admin.
                joined_date=joined_date,
                joined_ip_num=ip_addr,
                joined_remote_host=ip_addr
            )
            session.add(db_user)

            # Create a username.
            db_nick = models.DBUserNickname(
                user=db_user,
                nickname=username,
                flag_valid=1,
                flag_primary=1
            )

            # Create the user's profile.
            archive, subject_class = _random_category()
            db_profile = models.DBProfile(
                user=db_user,
                country='us',
                affiliation=affiliation,
                url=home_page,
                rank=random.randint(1, 5),
                archive=archive,
                subject_class=subject_class,
                original_subject_classes='',
                flag_group_math=1 if _prob(5) else 0,
                flag_group_cs=1 if _prob(5) else 0,
                flag_group_nlin=1 if _prob(5) else 0,
                flag_group_q_bio=1 if _prob(5) else 0,
                flag_group_q_fin=1 if _prob(5) else 0,
                flag_group_stat=1 if _prob(5) else 0
            )

            # Set the user's password.
            db_password = models.DBUserPassword(
                user=db_user,
                password_storage=2,
                password_enc=util.hash_password(password)
            )

            session.add(db_password)
            session.add(db_nick)
            session.add(db_profile)

            session.commit()


if __name__ == '__main__':
    create_user()
