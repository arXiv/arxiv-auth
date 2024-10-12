# arXiv Auth

This repo provides applications and libraries to support authentication and
authorization, including /login, user sessions, account creation(TBD) and API
token management(TBD).

In this repository there are the following:

1. [``arxiv-auth/``](arxiv-auth/) contains the ``arxiv-auth`` package which
   provides a Flask add on and other code for working with arxiv authenticated
   users in arXiv services.  This provides core authentication and authorization
   functions and domain classes and provides integrations with the legacy
   database for users and sessions.
2. [``accounts/``](accounts/) contains web app for the login/logout pages,
   registration (TBD), profile management(TBD), etc.
3. [``cloud_auth/``](cloud_auth/) **Not in use** authentication for use as a
   FastAPI dependency that checks legacy cookies, NG JWTs and GCP OAuth2 tokens.
3. [``authenticator/``](authenticator/) **Not in use** contains the
   authenticator service. Handles authentication requests from NGINX
   in a cloud deployment scenario.
4. [``registry/``](registry/) **Not in use** contains the API client
   registry application. This implements OAuth2 workflows, client
   registration, and the root API landing page.

# How to get started
To get started look to the README.md for the directory of the component you are
looking to use.

# TODO
- Investigate the state of the registry service and clean up, test and document if useful.

