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

VAULT_ENABLED = bool(int(os.environ.get('VAULT_ENABLED', '0')))
"""Enable/disable secret retrieval from Vault."""

KUBE_TOKEN = os.environ.get('KUBE_TOKEN', 'fookubetoken')
"""Service account token for authenticating with Vault. May be a file path."""

VAULT_HOST = os.environ.get('VAULT_HOST', 'foovaulthost')
"""Vault hostname/address."""

VAULT_PORT = os.environ.get('VAULT_PORT', '1234')
"""Vault API port."""

VAULT_ROLE = os.environ.get('VAULT_ROLE', 'authenticator')
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
     'minimum_ttl': 3600}
]
"""Requests for Vault secrets."""
