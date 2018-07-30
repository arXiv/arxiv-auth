"""Flask configuration."""

import os

VERSION = '0.2'

SECRET_KEY = os.environ.get('SECRET_KEY', 'asdf1234')
SERVER_NAME = os.environ.get('ACCOUNTS_SERVER_NAME')

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'nope')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'nope')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

LOGFILE = os.environ.get('LOGFILE')
LOGLEVEL = os.environ.get('LOGLEVEL', 20)

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DATABASE = os.environ.get('REDIS_DATABASE', '0')
REDIS_TOKEN = os.environ.get('REDIS_TOKEN', None)
"""This is the token used in the AUTH procedure."""


JWT_SECRET = os.environ.get('JWT_SECRET', 'foosecret')

DEFAULT_LOGIN_REDIRECT_URL = os.environ.get(
    'DEFAULT_LOGIN_REDIRECT_URL',
    'https://arxiv.org/user'
)
DEFAULT_LOGOUT_REDIRECT_URL = os.environ.get(
    'DEFAULT_LOGOUT_REDIRECT_URL',
    'https://arxiv.org'
)

SESSION_COOKIE_NAME = 'ARXIVNG_SESSION_ID'
SESSION_COOKIE_SECURE = bool(int(os.environ.get('SESSION_COOKIE_SECURE', '1')))

CLASSIC_COOKIE_NAME = os.environ.get('CLASSIC_COOKIE_NAME', 'tapir_session')
CLASSIC_PERMANENT_COOKIE_NAME = os.environ.get(
    'CLASSIC_PERMANENT_COOKIE_NAME',
    'tapir_permanent'
)
CLASSIC_TRACKING_COOKIE = os.environ.get('CLASSIC_TRACKING_COOKIE', 'browser')
CLASSIC_COOKIE_TIMEOUT = os.environ.get('CLASSIC_COOKIE_TIMEOUT', '86400')
CLASSIC_TOKEN_RECOVERY_TIMEOUT = os.environ.get(
    'CLASSIC_TOKEN_RECOVERY_TIMEOUT',
    '86400'
)
CLASSIC_SESSION_HASH = os.environ.get('CLASSIC_SESSION_HASH', 'foosecret')
CLASSIC_SESSION_TIMEOUT = os.environ.get(
    'CLASSIC_SESSION_TIMEOUT',
    '36000'
)

CLASSIC_DATABASE_URI = os.environ.get('CLASSIC_DATABASE_URI')
"""If not set, legacy database integrations will not be available."""

CAPTCHA_SECRET = os.environ.get('CAPTCHA_SECRET', 'foocaptcha')
"""Used to encrypt captcha answers, so that we don't need to store them."""


BASE_SERVER = os.environ.get('BASE_SERVER', 'arxiv.org')
URLS = [
    ("register", "/user/register", BASE_SERVER),
]
