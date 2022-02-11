# API support for use in FastAPI

Basic support for access to arXiv users in the legacy DB, NG JWTs and
GCP JWTs.

Intened for use with FastAPI. If FastAPI is installed
``arxiv.cloud_auth.fastapi.auth`` can be used in ``Depeneds()``.

The goals are support for JWTs and minimal
dependencies. ``arxiv-base`` and ``arxiv-auth`` are not needed for use
of this package.

There is no attempt to support parts of arxiv.user
``arxiv.users.auth.scopes`` or the redis session store in
``arxiv.users.auth.sessions.store``.


