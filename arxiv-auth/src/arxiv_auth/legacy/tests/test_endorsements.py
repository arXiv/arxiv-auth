"""Tests for :mod:`arxiv.users.legacy.endorsements` using a live test DB."""

import os
from unittest import TestCase, mock
from datetime import datetime
from pytz import timezone, UTC

from flask import Flask
from mimesis import Person, Internet, Datetime

from arxiv import taxonomy
from .. import endorsements, util, models
from ... import domain

EASTERN = timezone('US/Eastern')


class TestEndorsement(TestCase):
    """Tests for :func:`get_endorsements`."""

    def setUp(self):
        """Generate some fake data."""
        self.app = Flask('test')
        self.app.config['CLASSIC_SESSION_HASH'] = 'foohash'
        self.app.config['CLASSIC_COOKIE_NAME'] = 'tapir_session_cookie'
        self.app.config['SESSION_DURATION'] = '36000'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

        util.init_app(self.app)

        with self.app.app_context():
            util.create_all()
            with util.transaction() as session:
                person = Person('en')
                net = Internet()
                ip_addr = net.ip_v4()
                email = "foouser@agu.org"
                approved = 1
                deleted = 0
                banned = 0
                first_name = person.name()
                last_name = person.surname()
                suffix_name = person.title()
                joined_date = util.epoch(
                    Datetime('en').datetime().replace(tzinfo=EASTERN)
                )
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
                    joined_date=joined_date,
                    joined_ip_num=ip_addr,
                    joined_remote_host=ip_addr
                )
                session.add(db_user)

                self.user = domain.User(
                    user_id=str(db_user.user_id),
                    username='foouser',
                    email=db_user.email,
                    name=domain.UserFullName(
                        forename=db_user.first_name,
                        surname=db_user.last_name,
                        suffix=db_user.suffix_name
                    )
                )

            ok_patterns = ['%w3.org', '%aaas.org', '%agu.org', '%ams.org']
            bad_patterns = ['%.com', '%.net', '%.biz.%']

            with util.transaction() as session:
                for pattern in ok_patterns:
                    session.add(models.DBEmailWhitelist(
                        pattern=str(pattern)
                    ))
                for pattern in bad_patterns:
                    session.add(models.DBEmailBlacklist(
                        pattern=str(pattern)
                    ))

                session.add(models.DBEndorsementDomain(
                    endorsement_domain='test_domain',
                    endorse_all='n',
                    mods_endorse_all='n',
                    endorse_email='y',
                    papers_to_endorse=3
                ))

                for category, definition in taxonomy.CATEGORIES_ACTIVE.items():
                    if '.' in category:
                        archive, subject_class = category.split('.', 1)
                    else:
                        archive, subject_class = category, ''
                    session.add(models.DBCategory(
                        archive=archive,
                        subject_class=subject_class,
                        definitive=1,
                        active=1,
                        endorsement_domain='test_domain'
                    ))

    def test_get_endorsements(self):
        """Test :func:`endoresement.get_endorsements`."""
        with self.app.app_context():
            all_endorsements = set(
                endorsements.get_endorsements(self.user, compress=False)
            )
            all_possible = set(taxonomy.CATEGORIES_ACTIVE.keys())
            self.assertEqual(all_endorsements, all_possible)
            all_compressed = set(
                endorsements.get_endorsements(self.user, compress=True)
            )
            self.assertEqual(all_compressed, {"*.*"})

            # Exclude cs.NA, and verify compression output.
            all_endorsements.remove('cs.NA')

            some = endorsements.compress_endorsements(all_endorsements)
            for archive in taxonomy.ARCHIVES_ACTIVE.keys():
                if archive not in ['cs', 'test']:
                    self.assertIn(f"{archive}.*", some)
            for category, definition in taxonomy.CATEGORIES_ACTIVE.items():
                if definition['in_archive'] == 'cs' and category != 'cs.NA':
                    self.assertIn(category, some)
