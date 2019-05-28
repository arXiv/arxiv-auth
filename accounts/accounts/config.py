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
REDIS_PORT = os.environ.get('REDIS_PORT', '7000')
REDIS_DATABASE = os.environ.get('REDIS_DATABASE', '0')
REDIS_TOKEN = os.environ.get('REDIS_TOKEN', None)
"""This is the token used in the AUTH procedure."""
REDIS_CLUSTER = os.environ.get('REDIS_CLUSTER', '1')


JWT_SECRET = os.environ.get('JWT_SECRET', 'foosecret')

DEFAULT_LOGIN_REDIRECT_URL = os.environ.get(
    'DEFAULT_LOGIN_REDIRECT_URL',
    'https://arxiv.org/user'
)
DEFAULT_LOGOUT_REDIRECT_URL = os.environ.get(
    'DEFAULT_LOGOUT_REDIRECT_URL',
    'https://arxiv.org'
)

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

CAPTCHA_SECRET = os.environ.get('CAPTCHA_SECRET', 'foocaptcha')
"""Used to encrypt captcha answers, so that we don't need to store them."""

CAPTCHA_FONT = os.environ.get('CAPTCHA_FONT', None)

BASE_SERVER = os.environ.get('BASE_SERVER', 'arxiv.org')
URLS = [
    ("register", "/user/register", BASE_SERVER),
    ("lost_password", "/user/lost_password", BASE_SERVER),
    ("login", "/login", BASE_SERVER),
    ("account", "/user", BASE_SERVER)
]

CREATE_DB = bool(int(os.environ.get('CREATE_DB', 0)))

RELEASE_NOTES_URL = "https://confluence.cornell.edu/x/wtJyFQ"
RELEASE_NOTES_TEXT = "Accounts v0.2 released 2018-09-05"

# Starting with v0.3.1, set ``AUTH_UPDATED_SESSION_REF=True`` in your
# application config to rename ``request.session`` to ``request.auth``.
# ``request.auth`` will be the default name for the authenticated session
# starting in v0.4.1.
AUTH_UPDATED_SESSION_REF = True

# TODO: when we are ready to starting running accounts in k8s, we will need to
# enable these options and set up appropriate roles. - Erick
#
VAULT_ENABLED = False
"""Enable/disable secret retrieval from Vault."""
#
# KUBE_TOKEN = os.environ.get('KUBE_TOKEN', 'fookubetoken')
# """Service account token for authenticating with Vault. May be a file path."""
#
# VAULT_HOST = os.environ.get('VAULT_HOST', 'foovaulthost')
# """Vault hostname/address."""
#
# VAULT_PORT = os.environ.get('VAULT_PORT', '1234')
# """Vault API port."""
#
# VAULT_ROLE = os.environ.get('VAULT_ROLE', 'registry')
# """Vault role linked to this application's service account."""
#
# VAULT_CERT = os.environ.get('VAULT_CERT')
# """Path to CA certificate for TLS verification when talking to Vault."""
#
# VAULT_SCHEME = os.environ.get('VAULT_SCHEME', 'https')
# """Default is ``https``."""
#
# NS_AFFIX = '' if NAMESPACE == 'production' else f'-{NAMESPACE}'
#
# VAULT_REQUESTS = [
#     {'type': 'generic',
#      'name': 'JWT_SECRET',
#      'mount_point': f'secret{NS_AFFIX}/',
#      'path': 'jwt',
#      'key': 'jwt-secret',
#      'minimum_ttl': 3600},
#     {'type': 'aws',
#      'name': 'AWS_S3_CREDENTIAL',
#      'mount_point': f'aws{NS_AFFIX}/',
#      'role': os.environ.get('VAULT_CREDENTIAL')}
# ]
# """Requests for Vault secrets."""
