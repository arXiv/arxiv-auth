"""
Integrations with the legacy arXiv database for users and sessions.

This package provides integrations with legacy user and sessions data in the
classic DB. These components were pulled out as a separate package because
they are required by both the accounts service and the authn/z middlware,
and maintaining them in both places would create too much duplication.
"""

from . import sessions, exceptions, authenticate, models, accounts, util, \
    endorsements
from .util import create_all, init_app, current_session, drop_all, \
    is_configured
