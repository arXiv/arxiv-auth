"""Handles all baz-related requests."""

from typing import Tuple
from accounts import status
from accounts.services import baz
from accounts.domain import Baz

from typing import Optional

NO_BAZ = {'reason': 'could not find the baz'}
BAZ_WONT_GO = {'reason': 'could not get the baz'}


def get_baz(baz_id: int) -> Tuple[Optional[dict], int, dict]:
    """
    Retrieve a baz from the Baz service.

    Parameters
    ----------
    baz_id : int
        The unique identifier for the baz in question.

    Returns
    -------
    dict
        Some interesting information about the baz.
    int
        An HTTP status code.
    dict
        Some extra headers to add to the response.
    """
    try:
        the_baz: Baz = baz.retrieve_baz(baz_id)
        if the_baz is None:
            status_code = status.HTTP_404_NOT_FOUND
            baz_data = NO_BAZ
        else:
            status_code = status.HTTP_200_OK
            baz_data = {'foo': the_baz.foo, 'mukluk': the_baz.mukluk}
    except IOError:
        baz_data = BAZ_WONT_GO
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return baz_data, status_code, {}
