# ``arxiv-auth`` Library

This provides a Flask add on and other code for working with arxiv authenticated
users.

# Quick start
For use-cases to check if a request is from an authenticated arxiv user, do the
following:

1. Install this package into your virtual environment
2. Install :class:`arxiv_auth.auth.Auth` onto your application. This adds a
   function called for each request to Flask that adds an instance of
   :class:`arxiv_auth.domain.Session` at ``flask.request.auth`` if the client is
   authenticated.
3. Add to the ``flask.config`` to setup :class:`arxiv_auth.auth.Auth` and
   related classes
   
Here's an example of how you might do #2 and #3:
```
   from flask import Flask
   from arxiv.base import Base
   from arxiv_users import auth

   app = Flask(__name__)
   Base(app)

   # config settings required to use legacy auth 
   app.config['CLASSIC_SESSION_HASH'] = '{hash_private_secret}'
   app.config['CLASSIC_DATABASE_URI'] = '{your_sqlalchemy_db_uri_to_legacy_db'}
   app.config['SESSION_DURATION'] = 36000
   app.config['CLASSIC_COOKIE_NAME'] = 'tapir_session'

   auth.Auth(app)    # <- Install the Auth to get auth checks and request.auth

   @app.route("/")
   def are_you_logged_in():
       if request.auth is not None:
           return "<p>Hello, You are logged in.</p>"
       else:
           return "<p>Hello unknown client.</p>"
```

# /login page?
The code for the `/login` page lives in [`accounts`](./README-accounts.md).

# Checking endorsements

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
