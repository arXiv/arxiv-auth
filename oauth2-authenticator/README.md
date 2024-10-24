# oauth2/oidc based authentication service

This is a service that initiates the oauth2 log-in, gets oauth2 callback, and sets up the
legacy/arxivng session + cookies.

## login
/login endpoint redirects to oauth2 server

## callback
Once a user succeeds the log-in on the server, this gets a callback from it. 

This is where the session is created and the cookies are set up.


## logout

logout kills the tapir session, deletes oauth2 session, and invalidates the cookies.


## deployment

This is intended to run in a docker, and the web server reverse proxies to this container.
