"""
Integration with the distributed session store.

In this implementation, we use a key-value store to hold session data
in JSON format. When a session is created, a cookie value is created (a
JSON web token) that contains information sufficient to retrieve the session.

See :mod:`.store`.
"""

from . import store
