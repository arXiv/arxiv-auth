"""Provides functions that mutate :class:`.Thing`s."""

import random
from accounts.domain import Thing


def add_some_one_to_the_thing(the_thing: Thing) -> None:
    """
    Add some ones to the name of a :class:`.Thing`.

    Parameters
    ----------
    the_thing : :class:`.Thing`
    """
    the_thing.name += "1" * random.randint(1, 10)
