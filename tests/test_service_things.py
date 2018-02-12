"""Tests for :mod:`accounts.services.things`."""

from unittest import TestCase, mock
from datetime import datetime
from accounts.services import things
import sqlalchemy
from accounts.domain import Thing

from typing import Any


class TestThingGetter(TestCase):
    """The method :meth:`.get_a_thing` retrieves data about things."""

    def setUp(self) -> None:
        """Initialize an in-memory SQLite database."""
        from accounts.services import things
        self.things = things
        app = mock.MagicMock(
            config={
                # 'SQLALCHEMY_DATABASE_URI': 'mysql://bob:dole@localhost/ack',
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                'SQLALCHEMY_TRACK_MODIFICATIONS': False
            }, extensions={}, root_path=''
        )
        things.db.init_app(app)
        things.db.app = app
        things.db.create_all()

        self.data = dict(name='The first thing', created=datetime.now())
        self.dbthing = self.things.DBThing(**self.data) # type: ignore
        self.things.db.session.add(self.dbthing) # type: ignore
        self.things.db.session.commit() # type: ignore

    def tearDown(self) -> None:
        """Clear the database and tear down all tables."""
        things.db.session.remove()
        things.db.drop_all()

    def test_get_a_thing_that_exists(self) -> None:
        """When the thing exists, returns a :class:`.Thing`."""
        thing = self.things.get_a_thing(1) # type: ignore
        self.assertIsInstance(thing, Thing)
        self.assertEqual(thing.id, 1)
        self.assertEqual(thing.name, self.data['name'])
        self.assertEqual(thing.created, self.data['created'])

    def test_get_a_thing_that_doesnt_exist(self) -> None:
        """When the thing doesn't exist, returns None."""
        self.assertIsNone(things.get_a_thing(2))

    @mock.patch('accounts.services.things.db.session.query')
    def test_get_thing_when_db_is_unavailable(self, mock_query: Any) -> None:
        """When the database squawks, raises an IOError."""
        def raise_op_error(*args: str, **kwargs: str) -> None:
            raise sqlalchemy.exc.OperationalError('statement', {}, None)
        mock_query.side_effect = raise_op_error
        with self.assertRaises(IOError):
            self.things.get_a_thing(1) # type: ignore


class TestThingCreator(TestCase):
    """:func:`.store_a_thing` creates a new record in the database."""

    def setUp(self) -> None:
        """Initialize an in-memory SQLite database."""
        from accounts.services import things
        self.things = things
        app = mock.MagicMock(
            config={
                # 'SQLALCHEMY_DATABASE_URI': 'mysql://bob:dole@localhost/ack',
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                'SQLALCHEMY_TRACK_MODIFICATIONS': False
            }, extensions={}, root_path=''
        )
        self.things.db.init_app(app) # type: ignore
        self.things.db.app = app # type: ignore
        self.things.db.create_all() # type: ignore

        self.data = dict(name='The first thing', created=datetime.now())
        self.dbthing = self.things.DBThing(**self.data) # type: ignore
        self.things.db.session.add(self.dbthing) # type: ignore
        self.things.db.session.commit() # type: ignore

    def tearDown(self) -> None:
        """Clear the database and tear down all tables."""
        self.things.db.session.remove() # type: ignore
        self.things.db.drop_all() # type: ignore

    def test_store_a_thing(self) -> None:
        """A new row is added for the thing."""
        the_thing = Thing(name='The new thing', created=datetime.now())

        self.things.store_a_thing(the_thing) # type: ignore
        self.assertGreater(the_thing.id, 0, "Thing.id is updated with pk id")

        dbthing = self.things.db.session.query(self.things.DBThing).get(the_thing.id) # type: ignore

        self.assertEqual(dbthing.name, the_thing.name)


class TestThingUpdater(TestCase):
    """:func:`.update_a_thing` updates the db with :class:`.Thing` data."""

    def setUp(self) -> None:
        """Initialize an in-memory SQLite database."""
        from accounts.services import things
        self.things = things
        app = mock.MagicMock(
            config={
                # 'SQLALCHEMY_DATABASE_URI': 'mysql://bob:dole@localhost/ack',
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                'SQLALCHEMY_TRACK_MODIFICATIONS': False
            }, extensions={}, root_path=''
        )
        self.things.db.init_app(app) # type: ignore
        self.things.db.app = app # type: ignore
        self.things.db.create_all() # type: ignore

        self.data = dict(name='The first thing', created=datetime.now())
        self.dbthing = self.things.DBThing(**self.data) # type: ignore
        self.things.db.session.add(self.dbthing) # type: ignore
        self.things.db.session.commit() # type: ignore

    def tearDown(self) -> None:
        """Clear the database and tear down all tables."""
        self.things.db.session.remove() # type: ignore
        self.things.db.drop_all() # type: ignore

    def test_update_a_thing(self) -> None:
        """The db is updated with the current state of the :class:`.Thing`."""
        the_thing = Thing(id=self.dbthing.id, name='Whoops')
        self.things.update_a_thing(the_thing) # type: ignore

        dbthing = self.things.db.session.query(self.things.DBThing).get(self.dbthing.id) # type: ignore

        self.assertEqual(dbthing.name, the_thing.name)

    @mock.patch('accounts.services.things.db.session.query')
    def test_operationalerror_is_handled(self, mock_query: Any) -> None:
        """When the db raises an OperationalError, an IOError is raised."""
        the_thing = Thing(id=self.dbthing.id, name='Whoops')

        def raise_op_error(*args, **kwargs) -> None: # type: ignore
            raise sqlalchemy.exc.OperationalError('statement', {}, None)
        mock_query.side_effect = raise_op_error

        with self.assertRaises(IOError):
            self.things.update_a_thing(the_thing) # type: ignore

    def test_thing_really_does_not_exist(self) -> None:
        """If the :class:`.Thing` doesn't exist, a RuntimeError is raised."""
        the_thing = Thing(id=555, name='Whoops')    # Unlikely to exist.
        with self.assertRaises(RuntimeError):
            self.things.update_a_thing(the_thing) # type: ignore

    @mock.patch('accounts.services.things.db.session.query')
    def test_thing_does_not_exist(self, mock_query: Any) -> None:
        """If the :class:`.Thing` doesn't exist, a RuntimeError is raised."""
        the_thing = Thing(id=555, name='Whoops')    # Unlikely to exist.
        mock_query.return_value = mock.MagicMock(
            get=mock.MagicMock(return_value=None)
        )
        with self.assertRaises(RuntimeError):
            self.things.update_a_thing(the_thing) # type: ignore
