"""Describes the data that will be passed around inside of the service."""

from datetime import datetime
from typing import Type, Any, Optional


class Property(object):
    """Describes a named, typed property on a data structure."""

    def __init__(self, name: str, klass: Optional[Type] = None,
                 default: Any = None) -> None:
        """Set the name, type, and default value for the property."""
        self._name = name
        self.klass = klass
        self.default = default

    def __get__(self, instance: Any, owner: Optional[Type] = None) -> Any:
        """
        Retrieve the value of property from the data instance.

        Parameters
        ----------
        instance : object
            The data structure instance on which the property is set.
        owner : type
            The class/type of ``instance``.

        Returns
        -------
        object
            If the data structure is instantiated, returns the value of this
            property. Otherwise returns this :class:`.Property` instance.
        """
        if instance:
            if self._name not in instance.__dict__:
                instance.__dict__[self._name] = self.default
            return instance.__dict__[self._name]
        return self

    def __set__(self, instance: Any, value: Any) -> None:
        """
        Set the value of the property on the data instance.

        Parameters
        ----------
        instance : object
            The data structure instance on which the property is set.
        value : object
            The value to which the property should be set.

        Raises
        ------
        TypeError
            Raised when ``value`` is not an instance of the specified type
            for the property.
        """
        if self.klass is not None and not isinstance(value, self.klass):
            raise TypeError('Must be an %s' % self.klass.__name__)
        instance.__dict__[self._name] = value


class Data(object):
    """Base class for data domain classes."""

    def __init__(self, **data: Any) -> None:
        """Initialize with some data."""
        for key, value in data.items():
            if isinstance(getattr(self.__class__, key), Property):
                setattr(self, key, value)


class Baz(Data):
    """Baz est ut mi semper mattis non eget tellus."""

    foo = Property('foo', str)
    """Foo a tellus sit amet purus pharetra gravida vulputate ut purus."""

    mukluk = Property('mukluk', int)
    """A soft boot, traditionally made of reindeer skin or sealskin."""


class Thing(Data):
    """
    A thing in itself.

    The attention will tend toward the species either in such a way that it
    would not pass beyond so as to attend to the object, or in such a way that
    it would pass beyond. If in the first way, then the thing will not be seen
    in itself but only its image will be seen as if it were the thing itself.
    That is the role of a memory species, not a visual one. If in the second
    way, then after the inspection of the species it will inspect the object in
    itself. In this way it will cognize the object in two ways, first through
    the species and second in itself. It will indeed be like when someone sees
    an intervening space and then beyond that sees the fixed object.
    """

    id = Property('id', int)
    name = Property('name', str)
    """
    A thing that stands in for the object in the mind.

    When the exterior thing in-and-of-itself (per se) is not placed before the
    attention, there must be a memorative species placed before it in lieu of
    the object, which [the species] is not the origin of the cognitive act,
    except insofar as it serves as a term for or representative of the object.
    """

    created = Property('created', datetime)
    """
    Being is dynamic.

    The dynamic nature of being should be the primary focus of any
    comprehensive philosophical account of reality and our place within it.
    """
