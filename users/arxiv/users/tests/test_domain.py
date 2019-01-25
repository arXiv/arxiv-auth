"""Tests for :mod:`arxiv.users.domain`."""

from unittest import TestCase
from typing import NamedTuple, Optional
from datetime import datetime
from pytz import timezone, UTC

from ..auth import scopes
from .. import domain

EASTERN = timezone('US/Eastern')


class TestDictCoercion(TestCase):
    """Tests for :func:`domain.from_dict` and :func:`domain.to_dict`."""

    def test_minimal_class(self):
        """A minimal NamedTuple class is used, with no child tuple types."""
        class Simple(NamedTuple):
            foo: str

        simple = Simple(foo='bar')
        self.assertEqual(simple,
                         domain.from_dict(Simple, domain.to_dict(simple)))

    def test_class_with_children(self):
        """A NamedTuple class is used that has fields expecting NamedTuples."""
        class ChildClass(NamedTuple):
            foo: str

        class ParentClass(NamedTuple):
            baz: ChildClass

        parent = ParentClass(baz=ChildClass(foo='bar'))
        self.assertEqual(parent,
                         domain.from_dict(ParentClass, domain.to_dict(parent)))

    def test_class_with_nested_children(self):
        """Child NamedTuple classes are combined with nested Types."""
        class ChildClass(NamedTuple):
            foo: str
            bat: dict

        class ParentClass(NamedTuple):
            baz: Optional[ChildClass] = None

        parent = ParentClass(baz=ChildClass(foo='bar', bat={'qw': 'er'}))
        self.assertEqual(parent,
                         domain.from_dict(ParentClass, domain.to_dict(parent)))

        parent = ParentClass(baz=None)
        self.assertEqual(parent,
                         domain.from_dict(ParentClass, domain.to_dict(parent)))

    def test_class_with_datetime(self):
        """The NamedTuple class also includes datetime fields."""
        class ChildClass(NamedTuple):
            foo: datetime

        class ParentClass(NamedTuple):
            bat: Optional[datetime]
            baz: Optional[ChildClass] = None

        parent = ParentClass(bat=datetime.now(tz=UTC),
                             baz=ChildClass(foo=datetime.now(tz=UTC)))
        self.assertEqual(parent,
                         domain.from_dict(ParentClass, domain.to_dict(parent)))

    def test_with_session(self):
        session = domain.Session(
            session_id='asdf1234',
            start_time=datetime.now(), end_time=datetime.now(),
            user=domain.User(
                user_id='12345',
                email='foo@bar.com',
                username='emanresu',
                name=domain.UserFullName('First', 'Last', 'Lastest'),
                profile=domain.UserProfile(
                    affiliation='FSU',
                    rank=3,
                    country='us',
                    default_category=domain.Category('astro-ph', 'CO'),
                    submission_groups=['grp_physics']
                )
            ),
            authorizations=domain.Authorizations(
                scopes=[scopes.VIEW_SUBMISSION, scopes.CREATE_SUBMISSION],
                endorsements=[domain.Category('astro-ph', 'CO')]
            )
        )
        session_data = domain.to_dict(session)
        self.assertEqual(session_data['authorizations']['scopes'],
                         [{
                             'action': 'read',
                             'domain': 'submission',
                             'resource': None
                         },
                         {
                             'action': 'create',
                             'domain': 'submission',
                             'resource': None
                         }])
        self.assertEqual(session_data['authorizations']['endorsements'],
                         [{'archive': 'astro-ph', 'subject': 'CO'}])

        self.assertEqual(
            session_data['user']['profile'],
            {
                'affiliation': 'FSU',
                'country': 'us',
                'rank': 3,
                'submission_groups': ['grp_physics'],
                'default_category': {'archive': 'astro-ph', 'subject': 'CO'},
                'homepage_url': '',
                'remember_me': True
            }
        )
        self.assertEqual(
            session_data['user']['name'],
            {'forename': 'First', 'surname': 'Last', 'suffix': 'Lastest'}
        )

        as_session = domain.from_dict(domain.Session, session_data)
        self.assertEqual(session, as_session)
