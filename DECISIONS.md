# Decision log

1. To minimize complexity, we'll start with a managed Redis cluster in AWS
   ElastiCache. In the future, we may consider running our own HA key-value
   store, and potentially evaluate performance of other backends.
2. In NG session store, will need to attach auth scope information. For now we
   can decide what "admin", "moderator", etc means and inject the relevant
   scopes. Later on, we will have an RBAC system. We therefore screen off the
   scope-determination concern from the session-creation concern.

## 2019-02-28 Rename ``request.session`` to ``request.auth``

The auth middleware in ``arxiv.users`` package hands the authenticated session
on ``flask.session``, which clobbers the built-in Flask session interface. This
is a design flaw that's blocking other work. ARXIVNG-1920

Starting with v0.3.1, set ``AUTH_UPDATED_SESSION_REF=True`` in your
application config to rename ``request.session`` to ``request.auth``.
``request.auth`` will be the default name for the authenticated session
starting in v0.4.1.
