"""Tests for :mod:`arxiv.users.domain`."""

from unittest import TestCase
from typing import NamedTuple, Optional
from datetime import datetime
from pytz import timezone

from ..domain import from_dict, to_dict

EASTERN = timezone('US/Eastern')


class TestDictCoercion(TestCase):
    """Tests for :func:`domain.from_dict` and :func:`domain.to_dict`."""

    def test_minimal_class(self):
        """A minimal NamedTuple class is used, with no child tuple types."""
        class Simple(NamedTuple):
            foo: str

        simple = Simple(foo='bar')
        self.assertEqual(simple, from_dict(Simple, to_dict(simple)))

    def test_class_with_children(self):
        """A NamedTuple class is used that has fields expecting NamedTuples."""
        class ChildClass(NamedTuple):
            foo: str

        class ParentClass(NamedTuple):
            baz: ChildClass

        parent = ParentClass(baz=ChildClass(foo='bar'))
        self.assertEqual(parent, from_dict(ParentClass, to_dict(parent)))

    def test_class_with_nested_children(self):
        """Child NamedTuple classes are combined with nested Types."""
        class ChildClass(NamedTuple):
            foo: str
            bat: dict

        class ParentClass(NamedTuple):
            baz: Optional[ChildClass] = None

        parent = ParentClass(baz=ChildClass(foo='bar', bat={'qw': 'er'}))
        self.assertEqual(parent, from_dict(ParentClass, to_dict(parent)))

        parent = ParentClass(baz=None)
        self.assertEqual(parent, from_dict(ParentClass, to_dict(parent)))

    def test_class_with_datetime(self):
        """The NamedTuple class also includes datetime fields."""
        class ChildClass(NamedTuple):
            foo: datetime

        class ParentClass(NamedTuple):
            bat: Optional[datetime]
            baz: Optional[ChildClass] = None

        parent = ParentClass(bat=datetime.now(tz=EASTERN),
                             baz=ChildClass(foo=datetime.now(tz=EASTERN)))
        self.assertEqual(parent, from_dict(ParentClass, to_dict(parent)))
