"""Flask configuration."""
import secrets
import os
import re

#################### General config for app ####################
BASE_SERVER = os.environ.get('BASE_SERVER', 'arxiv.org')
"""Sets base server for use when doman name is needed.

The default configs for `DEFAULT_LOGIN_REDIRECT_URL` and
`DEFAULT_LOGOUT_REDIRECT_URL` and `AUTH_SESSION_COOKIE_DOMAIN` will use
this. They can be independently configured if needed.
"""

DEFAULT_LOGIN_REDIRECT_URL = os.environ.get(
    'DEFAULT_LOGIN_REDIRECT_URL',
    f'https://{BASE_SERVER}/user'
)
"""URL to redirect the user to on a successful login, if they have not provided
a `next_page` query param."""

DEFAULT_LOGOUT_REDIRECT_URL = os.environ.get(
    'DEFAULT_LOGOUT_REDIRECT_URL',
    f'https://{BASE_SERVER}'
)
"""URL to redirect the user to on a logout."""


_relative_urls = r"(^\/(?:[^\/]+\/)*[^\/]+$)"
_absolute_urls = rf"(^https://([a-zA-Z0-9\-.])*{re.escape(BASE_SERVER)}/.*$)"
LOGIN_REDIRECT_REGEX = os.environ.get('LOGIN_REDIRECT_REGEX',
                                      f"{_relative_urls}|{_absolute_urls}")
"""Regex to check next_page of /login.

Only next_page values that match this regex will be allowed. All
others will go to the DEFAULT_LOGOUT_REDIRECT_URL. The default value
for this allows relative URLs and URLs to subdomains of the
BASE_SERVER.
"""

login_redirect_pattern = re.compile(LOGIN_REDIRECT_REGEX)


#################### NG JWT Auth configs ####################
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '7000')
REDIS_DATABASE = os.environ.get('REDIS_DATABASE', '0')
REDIS_TOKEN = os.environ.get('REDIS_TOKEN', None)
"""This is the token used in the AUTH procedure."""
REDIS_CLUSTER = os.environ.get('REDIS_CLUSTER', '1')

REDIS_FAKE = os.environ.get('REDIS_FAKE', False)
"""Use the FakeRedis library instead of a redis service.

Useful for testing, dev, beta."""

JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_urlsafe(16))
"""JWT secret used with NG JWTs in `arxiv-auth`."""

AUTH_SESSION_COOKIE_NAME = 'ARXIVNG_SESSION_ID'
AUTH_SESSION_COOKIE_DOMAIN = os.environ.get('AUTH_SESSION_COOKIE_DOMAIN', f'.{BASE_SERVER}')
AUTH_SESSION_COOKIE_SECURE = bool(int(os.environ.get('AUTH_SESSION_COOKIE_SECURE', '1')))


#################### Classic Auth ####################
"""Classic tpair_session cookie based auth."""

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
CLASSIC_SESSION_HASH = os.environ.get('CLASSIC_SESSION_HASH', secrets.token_urlsafe(16))
SESSION_DURATION = os.environ.get(
    'SESSION_DURATION',
    '36000'
)

CLASSIC_DATABASE_URI = os.environ.get('CLASSIC_DATABASE_URI')
"""SQLALCHEMY_DATABASE_URI for legacy DB.

If not set, legacy database integrations will not be available."""

SQLALCHEMY_DATABASE_URI = CLASSIC_DATABASE_URI

SQLALCHEMY_TRACK_MODIFICATIONS = False

CREATE_DB = bool(int(os.environ.get('CREATE_DB', 0)))


#################### Minor configs ##############################
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(16))
"""Sets the `Flask` secret key used for sessions. Not directly used in arxiv auth."""

RELEASE_NOTES_URL = "https://github.com/arXiv/arxiv-auth/releases"
RELEASE_NOTES_TEXT = "Accounts v1.1.0"

CAPTCHA_SECRET = os.environ.get('CAPTCHA_SECRET', secrets.token_urlsafe(16))
"""Used to encrypt captcha answers, so that we don't need to store them.

Used by registration form."""

CAPTCHA_FONT = os.environ.get('CAPTCHA_FONT', None)
"""Used by registration form."""


#################### Supports arxiv-base ####################
URLS = [
    ("register", "/user/register", BASE_SERVER),
    ("lost_password", "/user/lost_password", BASE_SERVER),
    ("login", "/login", BASE_SERVER),
    ("account", "/user", BASE_SERVER)
]
"""`arxiv-base` will add these for use in `Flask` `url_for()`."""

FLASKS3_BUCKET_NAME = os.environ.get('FLASKS3_BUCKET_NAME', 'some_bucket')
FLASKS3_CDN_DOMAIN = os.environ.get('FLASKS3_CDN_DOMAIN', 'static.arxiv.org')
FLASKS3_USE_HTTPS = os.environ.get('FLASKS3_USE_HTTPS', 1)
FLASKS3_FORCE_MIMETYPE = os.environ.get('FLASKS3_FORCE_MIMETYPE', 1)
FLASKS3_ACTIVE = os.environ.get('FLASKS3_ACTIVE', 0)
"""Flask-S3 plugin settings."""

VERSION = '0.4'
APP_VERSION = '0.4'
"""The application version."""

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'nope')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'nope')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

LOGLEVEL = os.environ.get('LOGLEVEL', 20)
"""Used by base.logging but that package seems buggy so maybe remove"""

#################### Flask configs ####################
"""See https://flask.palletsprojects.com/en/2.3.x/config/"""

APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/')

#################### unused ####################
"""These are unused in auth and base """

LOGFILE = os.environ.get('LOGFILE')
