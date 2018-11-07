# Authenticator service

Lightweight service for authorizing requests.

Intended to be used in conjunction with NGINX's ngx_http_auth_request_module.
Requests handled by NGINX are first passed to this service, which responds with
either 200 (authorized) or 403 (unauthorized).

In this implementation, we validate the client's auth token, which is contained
either in the ``Authorization`` header or in a cookie, and (if valid)
return an encrypted JWT describing the user/client and its privileges.
NGINX inserts that token into the ``Authorization`` header when subsequently
proxying the request to the target service.
