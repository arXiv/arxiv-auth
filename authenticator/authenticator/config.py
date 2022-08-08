"""Flask configuration for authenticator service."""

import os

NAMESPACE = os.environ.get('NAMESPACE')
"""Namespace in which this service is deployed; to qualify keys for secrets."""

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '7000')
REDIS_DATABASE = os.environ.get('REDIS_DATABASE', '0')
REDIS_CLUSTER = os.environ.get('REDIS_CLUSTER', '1')
AUTH_SESSION_COOKIE_NAME = os.environ.get('AUTH_SESSION_COOKIE_NAME',
                                          'ARXIVNG_SESSION_ID')
JWT_SECRET = os.environ.get('JWT_SECRET', 'foosecret')

# Starting with v0.3.1, set ``AUTH_UPDATED_SESSION_REF=True`` in your
# application config to rename ``request.session`` to ``request.auth``.
# ``request.auth`` will be the default name for the authenticated session
# starting in v0.4.1.
AUTH_UPDATED_SESSION_REF = True
