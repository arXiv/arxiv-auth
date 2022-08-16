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
        util.init_app(self.app)
        self.app.config['CLASSIC_DATABASE_URI'] = 'sqlite:///test.db'
        self.app.config['CLASSIC_SESSION_HASH'] = 'foohash'

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

    def tearDown(self):
        """Remove the test DB."""
        try:
            os.remove('./test.db')
        except FileNotFoundError:
            pass

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


class TestAutoEndorsement(TestCase):
    """Tests for :func:`get_autoendorsements`."""

    def setUp(self):
        """Generate some fake data."""
        self.app = Flask('test')
        util.init_app(self.app)
        self.app.config['CLASSIC_DATABASE_URI'] = 'sqlite:///test.db'
        self.app.config['CLASSIC_SESSION_HASH'] = 'foohash'

        with self.app.app_context():
            util.create_all()
            with util.transaction() as session:
                person = Person('en')
                net = Internet()
                ip_addr = net.ip_v4()
                email = person.email()
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

    def tearDown(self):
        """Remove the test DB."""
        try:
            os.remove('./test.db')
        except FileNotFoundError:
            pass

    def test_invalidated_autoendorsements(self):
        """The user has two autoendorsements that have been invalidated."""
        with self.app.app_context():
            with util.transaction() as session:
                issued_when = util.epoch(
                    Datetime('en').datetime().replace(tzinfo=EASTERN)
                )
                session.add(models.DBEndorsement(
                    endorsee_id=self.user.user_id,
                    archive='astro-ph',
                    subject_class='CO',
                    flag_valid=0,
                    endorsement_type='auto',
                    point_value=10,
                    issued_when=issued_when
                ))
                session.add(models.DBEndorsement(
                    endorsee_id=self.user.user_id,
                    archive='astro-ph',
                    subject_class='CO',
                    flag_valid=0,
                    endorsement_type='auto',
                    point_value=10,
                    issued_when=issued_when
                ))
                session.add(models.DBEndorsement(
                    endorsee_id=self.user.user_id,
                    archive='astro-ph',
                    subject_class='CO',
                    flag_valid=1,
                    endorsement_type='auto',
                    point_value=10,
                    issued_when=issued_when
                ))
                session.add(models.DBEndorsement(
                    endorsee_id=self.user.user_id,
                    archive='astro-ph',
                    subject_class='CO',
                    flag_valid=1,
                    endorsement_type='user',
                    point_value=10,
                    issued_when=issued_when
                ))

            result = endorsements.invalidated_autoendorsements(self.user)
        self.assertEqual(len(result), 2, "Two revoked endorsements are loaded")

    def test_category_policies(self):
        """Load category endorsement policies from the database."""
        with self.app.app_context():
            with util.transaction() as session:
                session.add(models.DBCategory(
                    archive='astro-ph',
                    subject_class='CO',
                    definitive=1,
                    active=1,
                    endorsement_domain='astro-ph'
                ))
                session.add(models.DBEndorsementDomain(
                    endorsement_domain='astro-ph',
                    endorse_all='n',
                    mods_endorse_all='n',
                    endorse_email='y',
                    papers_to_endorse=3
                ))

            policies = endorsements.category_policies()
            category = domain.Category('astro-ph.CO')
            self.assertIn(category, policies, "Data are loaded for categories")
            self.assertEqual(policies[category]['domain'], 'astro-ph')
            self.assertFalse(policies[category]['endorse_all'])
            self.assertTrue(policies[category]['endorse_email'])
            self.assertEqual(policies[category]['min_papers'], 3)

    def test_domain_papers(self):
        """Get the number of papers published in each domain."""
        with self.app.app_context():
            with util.transaction() as session:
                # User owns three papers.
                session.add(models.DBPaperOwners(
                    document_id=1,
                    user_id=self.user.user_id,
                    flag_author=0,  # <- User is _not_ an author.
                    valid=1
                ))
                session.add(models.DBDocuments(
                    document_id=1,
                    paper_id='2101.00123',
                    dated=util.epoch(datetime.now(tz=UTC))
                ))
                session.add(models.DBDocumentInCategory(
                    document_id=1,
                    archive='cs',
                    subject_class='DL',
                    is_primary=1
                ))
                session.add(models.DBCategory(
                    archive='cs',
                    subject_class='DL',
                    definitive=1,
                    active=1,
                    endorsement_domain='firstdomain'
                ))
                # Here's another paper.
                session.add(models.DBPaperOwners(
                    document_id=2,
                    user_id=self.user.user_id,
                    flag_author=1,  # <- User is an author.
                    valid=1
                ))
                session.add(models.DBDocuments(
                    document_id=2,
                    paper_id='2101.00124',
                    dated=util.epoch(datetime.now(tz=UTC))
                ))
                session.add(models.DBDocumentInCategory(
                    document_id=2,
                    archive='cs',
                    subject_class='IR',
                    is_primary=1
                ))
                session.add(models.DBCategory(
                    archive='cs',
                    subject_class='IR',
                    definitive=1,
                    active=1,
                    endorsement_domain='firstdomain'
                ))
                # Here's a paper for which the user is an author.
                session.add(models.DBPaperOwners(
                    document_id=3,
                    user_id=self.user.user_id,
                    flag_author=1,
                    valid=1
                ))
                session.add(models.DBDocuments(
                    document_id=3,
                    paper_id='2101.00125',
                    dated=util.epoch(datetime.now(tz=UTC))
                ))
                # It has both a primary and a secondary classification.
                session.add(models.DBDocumentInCategory(
                    document_id=3,
                    archive='astro-ph',
                    subject_class='EP',
                    is_primary=1
                ))
                session.add(models.DBDocumentInCategory(
                    document_id=3,
                    archive='astro-ph',
                    subject_class='CO',
                    is_primary=0    # <- secondary!
                ))
                session.add(models.DBCategory(
                    archive='astro-ph',
                    subject_class='EP',
                    definitive=1,
                    active=1,
                    endorsement_domain='seconddomain'
                ))
                session.add(models.DBCategory(
                    archive='astro-ph',
                    subject_class='CO',
                    definitive=1,
                    active=1,
                    endorsement_domain='seconddomain'
                ))
            papers = endorsements.domain_papers(self.user)
            self.assertEqual(papers['firstdomain'], 2)
            self.assertEqual(papers['seconddomain'], 2)

    def test_is_academic(self):
        """Determine whether a user is academic based on email."""
        ok_patterns = ['%w3.org', '%aaas.org', '%agu.org', '%ams.org']
        bad_patterns = ['%.com', '%.net', '%.biz.%']
        with self.app.app_context():
            with util.transaction() as session:
                for pattern in ok_patterns:
                    session.add(models.DBEmailWhitelist(
                        pattern=str(pattern)
                    ))
                for pattern in bad_patterns:
                    session.add(models.DBEmailBlacklist(
                        pattern=str(pattern)
                    ))

            self.assertTrue(endorsements.is_academic(domain.User(
                user_id='2',
                email='someone@fsu.edu',
                username='someone'
            )))
            self.assertFalse(endorsements.is_academic(domain.User(
                user_id='2',
                email='someone@fsu.biz.edu',
                username='someone'
            )))
            self.assertTrue(endorsements.is_academic(domain.User(
                user_id='2',
                email='someone@aaas.org',
                username='someone'
            )))
            self.assertFalse(endorsements.is_academic(domain.User(
                user_id='2',
                email='someone@foo.com',
                username='someone'
            )))
