"""
Lightweight service for authorizing requests.

The authenticator service is a Flask application that handles client
authorization requests from NGINX.

In a cloud deployment scenario, upon request to the arXiv API or an
authenticated endpoint, NGINX issues a sub-request (via the
`ngx_http_auth_request_module`) to the authorization service including any
cookies or auth headers. The authenticator service is responsible for
interpreting any auth information on the request, and either returns 200 (OK)
if the request is authorized, 401 (Unauthorized) if auth information was not
available or invalid, or 403 (Forbidden) if the request is denied.

For our purposes, the authenticator service is mainly concerned with ensuring
that the request has valid authentication information. The authenticator
service includes in its response an encrypted JWT (see
:mod:`arxiv.user.auth.tokens`) that contains information about the user or
client session, including its authorization scopes (see
:mod:`arxiv.user.auth.scopes`).

.. _figure-authenticator-service-containers:

.. figure:: ../_static/diagrams/authenticator-service-containers.png


The authenticator service uses session keys and API auth tokens to retrieve
session information from the distributed session/token store.
"""
