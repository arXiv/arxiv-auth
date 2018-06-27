"""Generate synthetic data for testing and development purposes."""

import os
import sys
from typing import Tuple
sys.path.append('./arxiv')

from flask import Flask
from users import authorization, legacy

from typing import List
import random
from datetime import datetime
from mimesis import Person, Internet, Datetime
from mimesis import config as mimesis_config

from arxiv import taxonomy
from users.legacy import models, util, sessions
from users import domain

LOCALES = list(mimesis_config.SUPPORTED_LOCALES.keys())
COUNT = 500


def _random_category() -> Tuple[str, str]:
    category = random.choice(list(taxonomy.CATEGORIES.items()))
    archive = category[1]['in_archive']
    subject_class = category[0].split('.')[-1] if '.' in category[0] else ''
    return archive, subject_class


def _get_locale() -> str:
    return LOCALES[random.randint(0, len(LOCALES) - 1)]


app = Flask('test')
legacy.init_app(app)
app.config['CLASSIC_DATABASE_URI'] = 'sqlite:///test.db'
app.config['CLASSIC_SESSION_HASH'] = 'foohash'

with app.app_context():
    legacy.create_all()

    _users = []
    for i in range(COUNT):
        with util.transaction() as session:
            locale = _get_locale()
            person = Person(locale)
            net = Internet(locale)
            ip_addr = net.ip_v4()
            db_user = models.DBUser(
                first_name=person.name(),
                last_name=person.surname(),
                suffix_name=person.title(),
                share_first_name=1,
                share_last_name=1,
                email=person.email(),
                flag_approved=1 if random.randint(0, 100) < 90 else 0,
                flag_deleted=1 if random.randint(0, 100) < 2 else 0,
                flag_banned=1 if random.randint(0, 100) <= 1 else 0,
                share_email=8,
                email_bouncing=0,
                policy_class=2,  # Public user. TODO: consider admin, etc.
                joined_date=util.epoch(Datetime(locale).datetime()),
                joined_ip_num=ip_addr,
                joined_remote_host=ip_addr
            )
            db_nick = models.DBUserNickname(
                user=db_user,
                nickname=person.username(),
                flag_valid=1 if random.randint(0, 100) < 90 else 0,
                flag_primary=1
            )

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
            password = person.password()
            db_password = models.DBUserPassword(
                user=db_user,
                password_storage=2,
                password_enc=util.hash_password(password)
            )
            etype = random.choice(['auto', 'user', 'admin'])
            ecategory = random.choice(list(taxonomy.CATEGORIES.items()))
            archive, subject_class = _random_category()
            db_endorsement = models.DBEndorsement(
                endorsee_id=db_user.user_id,
                archive=archive,
                subject_class=subject_class,
                flag_valid=1,
                endorsement_type=etype,
                point_value=random.randint(-10, 10),
                issued_when=util.epoch(Datetime(locale).datetime())
            )
            if len(_users) > 0 and etype == 'auto':
                db_endorsement.endorser_id = random.choice(_users).user_id

            session.add(db_user)
            session.merge(db_password)
            session.merge(db_nick)
            session.merge(db_profile)
            session.merge(db_endorsement)
            _users.append(db_user)
            print('\t'.join([db_user.email, db_nick.nickname, password]))

    for db_user in _users:
        user = domain.User(
            user_id=str(db_user.user_id),
            username=db_nick.nickname,
            email=db_user.email,
            authorizations=domain.Authorizations(
                classic=util.compute_capabilities(db_user),
            ),
            name=domain.UserFullName(
                forename=db_user.first_name,
                surname=db_user.last_name,
                suffix=db_user.suffix_name
            )
        )
        net = Internet(_get_locale())
        ip_addr = net.ip_v4()
        session = sessions.create(user, ip_addr, ip_addr)
        # Make some of them invalid.
        if random.randint(0, 100) < 5:
            sessions.invalidate(session.cookie)
