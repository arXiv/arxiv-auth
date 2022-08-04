"""Flask configuration."""

import os
import re

VERSION = '0.4'
APP_VERSION = '0.4'
"""The application version."""

BASE_SERVER = os.environ.get('BASE_SERVER', 'arxiv.org')

NAMESPACE = os.environ.get('NAMESPACE')
"""Namespace in which this service is deployed; to qualify keys for secrets."""

SECRET_KEY = os.environ.get('SECRET_KEY', 'asdf1234')

APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/')

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'nope')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'nope')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

LOGFILE = os.environ.get('LOGFILE')
LOGLEVEL = os.environ.get('LOGLEVEL', 20)

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '7000')
REDIS_DATABASE = os.environ.get('REDIS_DATABASE', '0')
REDIS_TOKEN = os.environ.get('REDIS_TOKEN', None)
"""This is the token used in the AUTH procedure."""
REDIS_CLUSTER = os.environ.get('REDIS_CLUSTER', '1')

REDIS_FAKE = os.environ.get('REDIS_FAKE', False)
"""Use the FakeRedis library instead of a redis service.

Useful for testing, dev, beta."""


JWT_SECRET = os.environ.get('JWT_SECRET', 'foosecret')

DEFAULT_LOGIN_REDIRECT_URL = os.environ.get(
    'DEFAULT_LOGIN_REDIRECT_URL',
    'https://arxiv.org/user'
)
DEFAULT_LOGOUT_REDIRECT_URL = os.environ.get(
    'DEFAULT_LOGOUT_REDIRECT_URL',
    'https://arxiv.org'
)

LOGIN_REDIRECT_REGEX = os.environ.get('LOGIN_REDIRECT_REGEX',
                                      fr'(/.*)|(https://([a-zA-Z0-9\-.])*{re.escape(BASE_SERVER)}/.*)')
"""Regex to check next_page of /login.

Only next_page values that match this regex will be allowed. All
others will go to the DEFAULT_LOGOUT_REDIRECT_URL. The default value
for this allows relative URLs and URLs to subdomains of the
BASE_SERVER.
"""

login_redirect_pattern = re.compile(LOGIN_REDIRECT_REGEX)

AUTH_SESSION_COOKIE_NAME = 'ARXIVNG_SESSION_ID'
AUTH_SESSION_COOKIE_DOMAIN = os.environ.get('AUTH_SESSION_COOKIE_DOMAIN', '.arxiv.org')
AUTH_SESSION_COOKIE_SECURE = bool(int(os.environ.get('AUTH_SESSION_COOKIE_SECURE', '1')))

CLASSIC_COOKIE_NAME = os.environ.get('CLASSIC_COOKIE_NAME', 'tapir_session')
CLASSIC_PERMANENT_COOKIE_NAME = os.environ.get(
    'CLASSIC_PERMANENT_COOKIE_NAME',
    'tapir_permanent'
)
CLASSIC_TRACKING_COOKIE = os.environ.get('CLASSIC_TRACKING_COOKIE', 'browser')
CLASSIC_TOKEN_RECOVERY_TIMEOUT = os.environ.get(
    'CLASSIC_TOKEN_RECOVERY_TIMEOUT',
    '86400'
)
CLASSIC_SESSION_HASH = os.environ.get('CLASSIC_SESSION_HASH', 'foosecret')
SESSION_DURATION = os.environ.get(
    'SESSION_DURATION',
    '36000'
)

CLASSIC_DATABASE_URI = os.environ.get('CLASSIC_DATABASE_URI')
"""If not set, legacy database integrations will not be available."""

SQLALCHEMY_DATABASE_URI = CLASSIC_DATABASE_URI

SQLALCHEMY_TRACK_MODIFICATIONS = False

CAPTCHA_SECRET = os.environ.get('CAPTCHA_SECRET', 'foocaptcha')
"""Used to encrypt captcha answers, so that we don't need to store them."""

CAPTCHA_FONT = os.environ.get('CAPTCHA_FONT', None)

URLS = [
    ("register", "/user/register", BASE_SERVER),
    ("lost_password", "/user/lost_password", BASE_SERVER),
    ("login", "/login", BASE_SERVER),
    ("account", "/user", BASE_SERVER)
]

CREATE_DB = bool(int(os.environ.get('CREATE_DB', 0)))

RELEASE_NOTES_URL = "https://github.com/arXiv/arxiv-auth/releases"
RELEASE_NOTES_TEXT = "Accounts v0.4.2 released 2020-03-10"

# Starting with v0.3.1, set ``AUTH_UPDATED_SESSION_REF=True`` in your
# application config to rename ``request.session`` to ``request.auth``.
# ``request.auth`` will be the default name for the authenticated session
# starting in v0.4.1.
AUTH_UPDATED_SESSION_REF = True

NS_AFFIX = '' if NAMESPACE == 'production' else f'-{NAMESPACE}'

FLASKS3_BUCKET_NAME = os.environ.get('FLASKS3_BUCKET_NAME', 'some_bucket')
FLASKS3_CDN_DOMAIN = os.environ.get('FLASKS3_CDN_DOMAIN', 'static.arxiv.org')
FLASKS3_USE_HTTPS = os.environ.get('FLASKS3_USE_HTTPS', 1)
FLASKS3_FORCE_MIMETYPE = os.environ.get('FLASKS3_FORCE_MIMETYPE', 1)
FLASKS3_ACTIVE = os.environ.get('FLASKS3_ACTIVE', 0)
"""Flask-S3 plugin settings."""
