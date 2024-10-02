# arXiv Auth

Obsolete-README for arXiv NG

## keycloak_bend

Keycloak backend

## legacy_auth_provider

Tapir --> Keycloak migration

The connection between Tapir db based login and the keycloak.

## oauth2-authenticator

The endpoint that gets the callback from the keycloak and sets up the
session cookies.
Handles the cookie refresh as well


## keycloak_bend/pubsub-listener

Gets the changes of keycloak and send it out to gcp subsub.