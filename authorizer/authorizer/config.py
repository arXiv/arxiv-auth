"""Flask configuration for authorizer service."""

import os

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DATABASE = os.environ.get('REDIS_DATABASE', '0')
SESSION_COOKIE_NAME = os.environ.get('SESSION_COOKIE_NAME',
                                     'ARXIVNG_SESSION_ID')
JWT_SECRET = os.environ.get('JWT_SECRET', 'foosecret')
