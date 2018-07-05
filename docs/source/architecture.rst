Architecture
============

Overview
--------

The arXiv platform provides both anonymous and authenticated interfaces to
end-users (including moderators), API clients, and the arXiv operations team.
This project provides applications and libraries to support authentication and
authorization, including account creation and login, user sessions, and API
token management. TLS is considered an infrastructure concern, and is therefore
out of scope (albeit critical) for this project.

Objectives & Requirements
-------------------------

1. Users must be able to register for and log in to the arXiv site, and
   interact with parts of the platform that require authentication.
2. API clients must be able to authenticate with the arXiv site, and obtain
   secure authorization tokens using OAuth2 protocols.
3. Administrators must be able to grant and revoke authorization for specific
   actions and services within the arXiv platform, using a role-based system.
4. It must be possible to revoke access from a user or client, and have that
   revocation take effect immediately.
5. Accessing authentication and authorization information in an arXiv
   service/application must not require implementing new integrations; we need
   a single, consistent solution for authn/z concerns in Flask applications.
6. Services/applications deployed in the cloud must be able to obtain authn/z
   information without accessing a central database. Services/applications
   deployed on-premises must integrate with the legacy database so that users
   can seamlessly move between legacy and NG interfaces using the same session.

Solution Strategy
-----------------

The objectives above are separated into four distinct concerns, each addressed
by a separate piece of software:

- :ref:`User accounts service <user-accounts_service-containers>`, which is
  responsible for user registration, authentication, and role management.
- :ref:`API client registry <api-client-registry-containers>`, which is
  responsible for API client authentication, workflows for obtaining
  authorization tokens, and client access management.
- :ref:`Authorizer service <authorizer-service-containers>`, which is
  responsible for authorizing user/client requests (cloud only).
- An :ref:`auth library <auth-package>`, which provides middleware and other
  components for working with user/client sessions and authorization in arXiv
  services.


.. _figure-authnz-context:

.. figure:: _static/diagrams/authnz-context.png

   System context for authn/z services in arXiv.


.. _user-accounts_service-containers:

User accounts service
---------------------

The user accounts service is a Flask application that provides user interfaces
for account registration, profile management, and authentication. It also
provides administrative interfaces for user management and authorization roles.

User data encompasses account details, preferences, and authorization roles.
During the NG project, this will be tables in the legacy database for which
temporary integration is required. Ultimately, these data will be housed in a
standalone database.

Authenticated sessions are stored in a distributed session/token store. When a
user authenticates, they are issued a session key in the form of a secure
cookie. That key can be used by the authorizer service to retrieve session
details on subsequent requests to the accounts service or any other service.

During the NG project, authenticated sessions must continue to be available to
legacy web controller components. This means that the accounts service must
integrate with the relevant sessions-related tables in the legacy database,
and issue cookies that are compatible with those legacy sessions.

.. _figure-user-accounts-containers:

.. figure:: _static/diagrams/user-accounts-containers.png

   Containers in the user accounts system.

For details, see :py:mod:`accounts`.

.. _api-client-registry-containers:

API client registry service
---------------------------

The API client registry is a Flask application that provides user interfaces
for registering new API clients, and managing API access. Authenticated users
may register to obtain an API bearer token for public endpoints, and also to
request additional authorization for protected endpoints such as submission.
APIs are provided to support OAuth2 workflows for retrieving authorization
tokens. Finally, administrative interfaces provide visibility and management.

API client data encompasses details about the client, client tokens, and
client authorizations. These data are stored in a stand-alone data store.

Authorization tokens are registered in the distributed
session/token store upon creation, where they can be retrieved by the
authorizer service to authorize subsequent API requests.


.. _figure-client-registry-containers:

.. figure:: _static/diagrams/client-registry-containers.png

   Containers in the API client registry system.

For details, see ___


.. _authorizer-service-containers:

Authorizer service
------------------

The authorizer service is a Flask application that handles client authorization
requests from NGINX.

In a cloud deployment scenario, upon request to the arXiv
API or an authenticated endpoint, NGINX issues a sub-request to the
authorization service including any cookies or auth headers. The
authorization service is responsible for interpreting any auth information on
the request, and either returns 200 (OK) if the request is authorized, 401
(Unauthorized) if auth information was not available or invalid, or 403
(Forbidden) if the request is denied.

For our purposes, the authorizer service is mainly concerned with ensuring that
the request has valid authentication information. The authorizer service
includes in its response an encrypted JWT (see :mod:`arxiv.user.auth.tokens`)
that contains information about the user or client session, including its
authorization scopes (see :mod:`arxiv.user.auth.scopes`).

.. _figure-authorizer-service-containers:

.. figure:: _static/diagrams/authorizer-service-containers.png

   Authorizer service containers.


The authorizer service uses session keys and API auth tokens to retrieve
session information from the distributed session/token store.

For details, see ___.


.. _auth-package:

Authn/z package
---------------

This package provides core functionality for working with users and sessions
in arXiv-NG services. Housing these components in a library (separate from
service implementations) ensures that users and sessions are represented
and manipulated consistently.

In addition to NG components, this package also provides integrations with the
legacy user and session data in the classic database.

The user accounts, API client registry, and authorizer services all rely on
this package for domain representations and integration with the legacy
system.

See :mod:`arxiv.users`.
