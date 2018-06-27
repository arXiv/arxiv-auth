"""Test the legacy integration with synthetic data."""

import os
import sys
from typing import Tuple
from unittest import TestCase
from flask import Flask

from typing import List
import random
from datetime import datetime
from mimesis import Person, Internet, Datetime
from mimesis import config as mimesis_config

from arxiv import taxonomy
from .. import models, util, sessions, authenticate, exceptions
from ... import domain

LOCALES = list(mimesis_config.SUPPORTED_LOCALES.keys())


def _random_category() -> Tuple[str, str]:
    category = random.choice(list(taxonomy.CATEGORIES.items()))
    archive = category[1]['in_archive']
    subject_class = category[0].split('.')[-1] if '.' in category[0] else ''
    return archive, subject_class


def _get_locale() -> str:
    return LOCALES[random.randint(0, len(LOCALES) - 1)]


class TestBootstrap(TestCase):
    """Tests against legacy user integrations with fake data."""

    @classmethod
    def setUpClass(cls):
        """Generate some fake data."""
        cls.app = Flask('test')
        util.init_app(cls.app)
        cls.app.config['CLASSIC_DATABASE_URI'] = 'sqlite:///test.db'
        cls.app.config['CLASSIC_SESSION_HASH'] = 'foohash'

        with cls.app.app_context():
            util.create_all()
            COUNT = 50

            cls.users = []

            _users = []
            _domain_users = []
            for i in range(COUNT):
                with util.transaction() as session:
                    locale = _get_locale()
                    person = Person(locale)
                    net = Internet(locale)
                    ip_addr = net.ip_v4()
                    email = person.email()
                    approved = 1 if random.randint(0, 100) < 90 else 0
                    deleted = 1 if random.randint(0, 100) < 2 else 0
                    banned = 1 if random.randint(0, 100) <= 1 else 0
                    first_name = person.name()
                    last_name = person.surname()
                    suffix_name = person.title()
                    name = (first_name, last_name, suffix_name)
                    db_user = models.DBUser(
                        first_name=first_name,
                        last_name=last_name,
                        suffix_name=suffix_name,
                        share_first_name=1,
                        share_last_name=1,
                        email=email,
                        flag_approved=approved,
                        flag_deleted=deleted,
                        flag_banned=banned,
                        flag_edit_users=0,
                        flag_edit_system=0,
                        flag_email_verified=1,
                        share_email=8,
                        email_bouncing=0,
                        policy_class=2,  # Public user. TODO: consider admin.
                        joined_date=util.epoch(Datetime(locale).datetime()),
                        joined_ip_num=ip_addr,
                        joined_remote_host=ip_addr
                    )
                    session.add(db_user)

                    # Create a username.
                    username_is_valid = 1 if random.randint(0, 100) < 90 else 0
                    username = person.username()
                    db_nick = models.DBUserNickname(
                        user=db_user,
                        nickname=username,
                        flag_valid=username_is_valid,
                        flag_primary=1
                    )

                    # Create the user's profile.
                    archive, subject_class = _random_category()
                    db_profile = models.Profile(
                        user=db_user,
                        country=locale,
                        affiliation=person.university(),
                        url=net.home_page(),
                        rank=random.randint(1, 5),
                        archive=archive,
                        subject_class=subject_class,
                        original_subject_classes='',
                        flag_group_math=1 if random.randint(0, 100) < 5 else 0,
                        flag_group_cs=1 if random.randint(0, 100) < 5 else 0,
                        flag_group_nlin=1 if random.randint(0, 100) < 5 else 0,
                        flag_group_q_bio=1 if random.randint(0, 100) < 5 else 0,
                        flag_group_q_fin=1 if random.randint(0, 100) < 5 else 0,
                        flag_group_stat=1 if random.randint(0, 100) < 5 else 0
                    )

                    # Set the user's password.
                    password = person.password()
                    db_password = models.DBUserPassword(
                        user=db_user,
                        password_storage=2,
                        password_enc=util.hash_password(password)
                    )

                    # Create some endorsements.
                    archive, subject_class = _random_category()
                    net_points = 0
                    for _ in range(0, random.randint(1, 4)):
                        etype = random.choice(['auto', 'user', 'admin'])
                        point_value = random.randint(-10, 10)
                        net_points += point_value
                        if len(_users) > 0 and etype == 'auto':
                            endorser_id = random.choice(_users).user_id
                        else:
                            endorser_id = None
                        session.add(models.DBEndorsement(
                            endorsee=db_user,
                            endorser_id=endorser_id,
                            archive=archive,
                            subject_class=subject_class,
                            flag_valid=1,
                            endorsement_type=etype,
                            point_value=point_value,
                            issued_when=util.epoch(Datetime(locale).datetime())
                        ))

                    session.add(db_password)
                    session.add(db_nick)
                    session.add(db_profile)
                    _users.append(db_user)
                    _domain_users.append((
                        domain.User(
                            user_id=str(db_user.user_id),
                            username=db_nick.nickname,
                            email=db_user.email,
                            name=domain.UserFullName(
                                forename=db_user.first_name,
                                surname=db_user.last_name,
                                suffix=db_user.suffix_name
                            )
                        ),
                        domain.Authorizations(
                            classic=util.compute_capabilities(db_user),
                        )
                    ))
                    session.commit()
                    # We'll use these data to run tests.
                    cls.users.append((
                        email, username, password, name,
                        (archive, subject_class, net_points),
                        (approved, deleted, banned),
                    ))

    def test_authenticate_and_use_session(self):
        """Attempt to authenticate users and create/load auth sessions."""
        with self.app.app_context():
            for datum in self.users:
                email, username, password, name, endorsement, status = datum
                approved, deleted, banned = status

                # Approved users may log in.
                if approved and not deleted and not banned:
                    user, auths = authenticate.authenticate(email, password)
                    self.assertIsInstance(user, domain.User,
                                          "User data is returned")
                    self.assertEqual(user.email, email,
                                     "Email is set correctly")
                    self.assertEqual(user.username, username,
                                     "Username is set correctly")

                    first_name, last_name, suffix_name = name
                    self.assertEqual(user.name.forename, first_name,
                                     "Forename is set correctly")
                    self.assertEqual(user.name.surname, last_name,
                                     "Surname is set correctly")
                    self.assertEqual(user.name.suffix, suffix_name,
                                     "Suffix is set correctly")
                    self.assertIsInstance(auths, domain.Authorizations,
                                          "Authorizations data are returned")
                    if endorsement[2] > 0:
                        self.assertIn(
                            domain.Category(archive=endorsement[0],
                                            subject=endorsement[1]),
                            auths.endorsements,
                            "Endorsements are included in authorizations"
                        )

                # Banned or deleted users may not log in.
                elif deleted or banned:
                    with self.assertRaises(exceptions.AuthenticationFailed):
                        authenticate.authenticate(email, password)
                    continue

                # Users who are not approved may not log in.
                elif not approved:
                    with self.assertRaises(exceptions.AuthenticationFailed):
                        authenticate.authenticate(email, password)
                    continue

                locale = _get_locale()
                net = Internet(locale)
                ip = net.ip_v4()
                session, cookie = sessions.create(user, auths, ip, ip)

                session_loaded = sessions.load(cookie)
                self.assertEqual(session.user, session_loaded.user,
                                 "Loaded the correct user")
                self.assertEqual(session.session_id, session_loaded.session_id,
                                 "Loaded the correct session")

                # Invalidate 10% of the sessions, and try again.
                if random.randint(0, 100) < 10:
                    sessions.invalidate(cookie)
                    with self.assertRaises(exceptions.SessionExpired):
                        sessions.load(cookie)
