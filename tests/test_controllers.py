"""Tests for :mod:`accounts.controllers`."""

from unittest import TestCase, mock
from datetime import datetime
from typing import Any
from accounts.factory import create_web_app
from accounts.domain import Baz, Thing
from accounts.controllers import baz, things


class TestBazController(TestCase):
    """Test the :mod:`accounts.controllers.baz` controller."""

    @mock.patch('accounts.services.baz.retrieve_baz')
    def test_get_baz(self, mock_retrieve_baz: Any) -> None:
        """:func:`.baz.get_baz` gets a Baz from the ``baz`` service."""
        mock_retrieve_baz.return_value = Baz(foo='bar', mukluk=1)

        response_data, status_code, headers = baz.get_baz(1)
        if isinstance(response_data, dict):
            self.assertDictEqual(response_data, {'foo': 'bar', 'mukluk': 1})
        else:
            self.fail('Expected a dict')
        self.assertEqual(status_code, 200)

        mock_retrieve_baz.return_value = None
        response_data, status_code, headers = baz.get_baz(1)
        self.assertEqual(status_code, 404)

    @mock.patch('accounts.services.baz.retrieve_baz')
    def test_baz_service_chokes(self, mock_retrieve_baz: Any) -> None:
        """If the :mod:`.services.baz` chokes, returns 500."""
        mock_retrieve_baz.side_effect = IOError
        response_data, status_code, headers = baz.get_baz(1)
        self.assertEqual(status_code, 500)


class TestThingController(TestCase):
    """Test the :mod:`accounts.controllers.things` controller."""

    @mock.patch('accounts.services.things.get_a_thing')
    def test_get_thing(self, mock_get_a_thing: Any) -> None:
        """:func:`.things.get_thing` gets a Thing from ``things`` service."""
        created = datetime.now()
        mock_get_a_thing.return_value = Thing(
            id=5,
            created=created,
            name='Thing!'
        )
        response_data, status_code, headers = things.get_thing(5)

        if isinstance(response_data, dict):
            self.assertDictEqual(response_data,
                                 {'name': 'Thing!',
                                  'created': created, 'id': 5})
        else:
            self.fail('Expected dict')
        self.assertEqual(status_code, 200)

        mock_get_a_thing.return_value = None
        response_data, status_code, headers = things.get_thing(5)
        self.assertEqual(status_code, 404)

    @mock.patch('accounts.services.things.get_a_thing')
    def test_things_service_chokes(self, mock_get_a_thing: Any) -> None:
        """If the :mod:`.services.baz` chokes, returns 500."""
        mock_get_a_thing.side_effect = IOError
        response_data, status_code, headers = things.get_thing(5)
        self.assertEqual(status_code, 500)

    @mock.patch('accounts.services.things.store_a_thing')
    def test_create_a_thing(self, mock_store_a_thing: Any) -> None:
        """Create a new :class:`.Thing` and store it."""
        thing_data = {'name': 'a new thing'}

        def _store(a_thing: Thing) -> Thing:
            a_thing.id = 5
            return a_thing
        mock_store_a_thing.side_effect = _store

        response_data, status_code, headers = things.create_a_thing(thing_data)
        self.assertEqual(status_code, 201, "Created")
        if isinstance(response_data, dict):
            self.assertEqual(response_data['id'], 5)
            self.assertEqual(response_data['name'], 'a new thing')
        else:
            self.fail('Expected a dict')
        self.assertIn('Location', headers)
