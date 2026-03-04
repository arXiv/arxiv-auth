# arXiv Auth

This repo provides applications and libraries for authentication and
authorization, including login, user sessions, account creation.

This repo is in the process of being phased out and replaced by keycloak/wombat.

It has the following directories:

1. [``arxiv-auth/``](arxiv-auth/) contains the ``arxiv-auth`` package which
   provides a Flask add on and other code for working with arxiv authenticated
   users in arXiv services.  This provides core authentication and authorization
   functions and domain classes and provides integrations with the legacy
   database for users and sessions.
2. [``accounts/``](accounts/) contains web app for the login/logout pages
3. [``cloud_auth/``](cloud_auth/) **Not in use** authentication for use as a
   FastAPI dependency that checks legacy cookies, NG JWTs and GCP OAuth2 tokens.

# How to get started
To get started look to the README.md for the directory of the component you are
looking to use.
