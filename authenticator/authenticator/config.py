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
