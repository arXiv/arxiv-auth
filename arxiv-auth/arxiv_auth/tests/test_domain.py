"""Tests for :mod:`arxiv.users.domain`."""

from unittest import TestCase
from datetime import datetime
from arxiv_auth.domain import Session
from pytz import timezone
from ..auth import scopes
from .. import domain

EASTERN = timezone('US/Eastern')


class TestSession(TestCase):
    def test_with_session(self):
        session = domain.Session(
            session_id='asdf1234',
            start_time=datetime.now(), end_time=datetime.now(),
            user=domain.User(
                user_id='12345',
                email='foo@bar.com',
                username='emanresu',
                name=domain.UserFullName(forename='First', surname='Last', suffix='Lastest'),
                profile=domain.UserProfile(
                    affiliation='FSU',
                    rank=3,
                    country='us',
                    default_category=domain.Category('astro-ph.CO'),
                    submission_groups=['grp_physics']
                )
            ),
            authorizations=domain.Authorizations(
                scopes=[scopes.VIEW_SUBMISSION, scopes.CREATE_SUBMISSION],
                endorsements=[domain.Category('astro-ph.CO')]
            )
        )
        session_data = session.dict()
        self.assertEqual(session_data['authorizations']['scopes'],
                         ['submission:read','submission:create'])
        self.assertEqual(session_data['authorizations']['endorsements'],
                         ['astro-ph.CO'])

        self.assertEqual(
            session_data['user']['profile'],
            {
                'affiliation': 'FSU',
                'country': 'us',
                'rank': 3,
                'submission_groups': ['grp_physics'],
                'default_category': 'astro-ph.CO',
                'homepage_url': '',
                'remember_me': True
            }
        )
        self.assertEqual(
            session_data['user']['name'],
            {'forename': 'First', 'surname': 'Last', 'suffix': 'Lastest'}
        )

        as_session = domain.session_from_dict(session_data)
        self.assertEqual(session, as_session)
