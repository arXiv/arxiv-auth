"""
API client registry service

The API client registry is a Flask application that provides user interfaces
for registering new API clients, and managing API access. Authenticated users
may register to obtain an API bearer token for public endpoints, and also to
request additional authorization for protected endpoints such as submission.

The system provides endpoints to support OAuth2 flows for external API
consumers that provide services to users, as well as an endpoint to retrieve a
bearer token for non-user-specific requests. Those endpoints are proxied by the
API Gateway.

End users (e.g. readers) can find useful applications and services, or
interesting research projects, registered with the application system.

API client data encompasses details about the client, client tokens, and
client authorizations. These data are stored in a stand-alone data store.

Authorization tokens are registered in the distributed
session/token store upon creation, where they can be retrieved by the
authenticator service to authorize subsequent API requests.

.. _figure-client-registry-containers:

.. figure:: ../_static/diagrams/client-registry-containers.png

   Containers in the API client registry system.

"""
