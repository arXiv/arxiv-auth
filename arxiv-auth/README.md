# ``arxiv-auth`` Library

This is the code that gets uploaded to pypy as arxiv-auth. The code
for the `/login` pages lives in [`accounts`](../accounts).

This package provides core functionality for working with users and
sessions in arXiv services. Housing these components in a library
separate from service implementations facilitates consistent
represention and manipulation of users and sessions.

This package provides core functionality for working with users and
sessions in arXiv services. Housing these components in a library
(separate from service implementations) ensures that users and
sessions are represented and manipulated consistently. In addition to
newer components, this package also provides integrations with the
legacy user and session data in the classic database.

The user accounts, API client registry, and authenticator services all rely on
this package for domain representations and integration with the legacy
system.

# Quick start
For typical use-cases, you will need to do the following:

1. Install this package into your virtual environment.
2. Install :class:`arxiv_auth.auth.Auth` onto your application. This will make
   information about the current authenticated :class:`.domain.Session`
   available to you on the Flask request proxy object as
   ``flask.request.auth``.
3. Install :class:`arxiv_users.auth.middleware.AuthMiddleware` onto your
   application. Optional (see below).

Here's an example of how you might do #2 and #3:
```
   # yourapp/factory.py
   from arxiv.base import Base
   from arxiv.base.middleware import wrap
   from arxiv_users import auth

   def create_web_app() -> Flask:
       app = Flask('foo')
       Base(app)
       auth.Auth(app)    # <- Install the Auth extension.
       wrap(app, [auth.middleware.AuthMiddleware])    # <- Install middleware.
       return app
```
If you are not deploying this application in the cloud behind NGINX (and
therefore will not support sessions from the distributed store), you do not
need the auth middleware (step #3).

Checking endorsements
---------------------
Endorsements for submission are represented as categories on the
:class:`.Authorization` object (generally
``session.authorizations.endorsements``). To avoid enumerating all of
the categories and archives in the system, we compress endorsed
categories wherever possible using wildcard notation. For example,
``cs.*`` represents an endorsement for all subjects in the ``cs``
archive. ``*.*`` represents an endorsement for all categories in the
system.

For convenience, endorsement authorizations can be checked with the
:meth:`.Authorizations.endorsed_for` method. For example:

```
   from flask import request

   if request.auth.authorizations.endorsed_for("cs.AI"):
       print("This user/client is endorsed for cs.AI")
```


