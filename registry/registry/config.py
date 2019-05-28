"""Flask configuration."""

import os

NAMESPACE = os.environ.get('NAMESPACE')
"""Namespace in which this service is deployed; to qualify keys for secrets."""

SECRET_KEY = os.environ.get('SECRET_KEY', 'asdf1234')
SERVER_NAME = os.environ.get('REGISTRY_SERVER_NAME')

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
"""If 1, expects a redis cluster; otherwise expects a single redis node."""


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
AUTH_SESSION_COOKIE_SECURE = \
    bool(int(os.environ.get('AUTH_SESSION_COOKIE_SECURE', '1')))

EXTERNAL_URL_SCHEME = os.environ.get('EXTERNAL_URL_SCHEME', 'https')
BASE_SERVER = os.environ.get('BASE_SERVER', 'arxiv.org')
URLS = [
    ("login", "/login", BASE_SERVER),
    ("register", "/register", BASE_SERVER),
    ("lost_password", "/lost_password", BASE_SERVER),
]

REGISTRY_DATABASE_URI = os.environ.get('REGISTRY_DATABASE_URI', 'sqlite://')
CREATE_DB = bool(int(os.environ.get('CREATE_DB', 0)))

# Starting with v0.3.1, set ``AUTH_UPDATED_SESSION_REF=True`` in your
# application config to rename ``request.session`` to ``request.auth``.
# ``request.auth`` will be the default name for the authenticated session
# starting in v0.4.1.
AUTH_UPDATED_SESSION_REF = True

VAULT_ENABLED = bool(int(os.environ.get('VAULT_ENABLED', '0')))
"""Enable/disable secret retrieval from Vault."""

KUBE_TOKEN = os.environ.get('KUBE_TOKEN', 'fookubetoken')
"""Service account token for authenticating with Vault. May be a file path."""

VAULT_HOST = os.environ.get('VAULT_HOST', 'foovaulthost')
"""Vault hostname/address."""

VAULT_PORT = os.environ.get('VAULT_PORT', '1234')
"""Vault API port."""

VAULT_ROLE = os.environ.get('VAULT_ROLE', 'registry')
"""Vault role linked to this application's service account."""

VAULT_CERT = os.environ.get('VAULT_CERT')
"""Path to CA certificate for TLS verification when talking to Vault."""

VAULT_SCHEME = os.environ.get('VAULT_SCHEME', 'https')
"""Default is ``https``."""

NS_AFFIX = '' if NAMESPACE == 'production' else f'-{NAMESPACE}'

VAULT_REQUESTS = [
    {'type': 'generic',
     'name': 'JWT_SECRET',
     'mount_point': f'secret{NS_AFFIX}/',
     'path': 'jwt',
     'key': 'jwt-secret',
     'minimum_ttl': 3600},
    {'type': 'aws',
     'name': 'AWS_S3_CREDENTIAL',
     'mount_point': f'aws{NS_AFFIX}/',
     'role': os.environ.get('VAULT_CREDENTIAL')},
    {'type': 'database',
     'engine': os.environ.get('REGISTRY_DATABASE_ENGINE', 'mysql+mysqldb'),
     'host': os.environ.get('REGISTRY_DATABASE_HOST', 'localhost'),
     'database': os.environ.get('REGISTRY_DATABASE', 'registry'),
     'params': 'charset=utf8mb4',
     'port': '3306',
     'name': 'REGISTRY_DATABASE_URI',
     'mount_point': f'database{NS_AFFIX}/',
     'role': 'registry-write'}
]
"""Requests for Vault secrets."""
