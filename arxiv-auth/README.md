# ``arxiv-auth`` Library

This is the code that gets uploaded to pypy as arxiv-auth. The code
for the `/login` page lives in [`accounts`](../accounts).

This package provides functionality for working with arxiv users in arXiv
services. This package provides the new JWT functionality and legacy user and
session data in the classic database.

Housing these components in a library separate from web apps ensures that users
and sessions are represented and manipulated consistently. The login+logout, user
accounts(TBD), API client registry(TBD), and authenticator(TBD) services all
rely on this package.

# Quick start
For typical use-cases where you want to check if a request is from an
authenticated arxiv user, you will need to do the following:

1. Install this package into your virtual environment.
2. Install :class:`arxiv_auth.auth.Auth` onto your application. This will make
   information about the current authenticated :class:`.domain.Session`
   available to you on the Flask request proxy object as
   ``flask.request.auth``.
3. Add to the ``flask.config`` to setup :class:`arxiv_auth.auth.Auth` and
   related classes.
   
Here's an example of how you might do #2 and #3:
```
   from flask import Flask
   from arxiv.base import Base
   from arxiv.base.middleware import wrap
   from arxiv_users import auth

   app = Flask(__name__)
   Base(app)
   # TODO WHAT CONFIG IS NEEDED?
   auth.Auth(app)    # <- Install the Auth to get auth checks and request.auth

   @app.route("/")
   def are_you_logged_in():
       if request.auth is not None:
           return "<p>Hello, You are logged in.</p>"
       else:
           return "<p>Hello unknown client.</p>"
```

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

Middleware
----------
In during NG there was middleware for arxiv-auth that could be used in NGINX to
do the authentication there. As of 2023 it is not in use.

See :class:`arxiv_users.auth.middleware.AuthMiddleware`

If you are not deploying this application in the cloud behind NGINX (and
therefore will not support sessions from the distributed store), you do not
need the auth middleware.
