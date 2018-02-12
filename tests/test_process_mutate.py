"""Tests for :mod:`accounts.process.mutate`."""

from unittest import TestCase
from datetime import datetime
from accounts.domain import Thing
from accounts.process.mutate import add_some_one_to_the_thing


class TestMutateThing(TestCase):
    """:func:`.add_some_one_to_the_thing` adds ones to :prop:`.Thing.name`."""

    def test_add_some_one(self) -> None:
        """The number of ones varies between 1 and 10."""
        a_thing = Thing(id=5, name='foo', created=datetime.now())
        add_some_one_to_the_thing(a_thing)
        N_after = len([c for c in a_thing.name if c == '1'])
        self.assertGreater(N_after, 0)
        self.assertLess(N_after, 11)
