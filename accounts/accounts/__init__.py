"""
arXiv accounts service.

The user accounts service is a Flask application that provides external user
interfaces for account registration, profile management, and authentication, as
well as backend APIs that provide user information to other arXiv services. It
also provides administrative interfaces for user management and authorization
roles. It is the primary repository for user data. User data encompasses
account details, preferences, and authorization roles.

This service is responsible for the primary user accounts database.
Transferring that responsibility from the classic system to this NG service is
an important milestone in the project. In order to maintain
integrations with the classic system, in early stages of the project the
accounts service will use the classic relational database as its primary
datastore, and will register user sessions via both the classic system and the
distributed key-store in parallel.

Context
-------
Users--including readers, submitters, moderators, and administrators--can
create and manage their accounts via a browser-facing interface. Users can
(re)set their password, add contact information, and manage their identity by
adding external identifiers (e.g. ORCIDs) to their accounts. Users are
identified across the arXiv.org system by their UUID.

Administrators can audit and intervene on user accounts and API applications
through a management interface.

Any user-facing applications that require authentication redirect users to a
login view provided by the user management system.

During the NG project, the accounts service integrates with the legacy database
to authenticate users, and create legacy sessions. Eventually, these data will
be migrated to a standalone database.

The accounts service also creates new sessions a distributed session/token
store, which allows applications :ref:`deployed in the cloud
<orchestration-kubernetes>` to leverage authorized sessions. When a user
authenticates, they are issued a session key in the form of a secure
cookie. That key can be used by the authenticator service to retrieve session
details on subsequent requests to the accounts service or any other service.

.. _figure-user-accounts-containers:

.. figure:: ../_static/diagrams/user-accounts-containers.png

   Containers in the user accounts system.

"""
