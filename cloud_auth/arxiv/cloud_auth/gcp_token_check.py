"""Package to check if a GCP token is valid

The goal of this is to allow code running with service account
credentials in GCP to authenticate with an API and make REST calls.

This works by associating a GCP service account email with an email of
a user in the arXiv tapir_users table. When you make an arxiv account
for a service account email, make sure to set its flag_email_verified
to 1.

To create tokens:

    import urllib
    import google.auth.transport.requests
    import google.oauth2.id_token

    service_url = "https://mod.arxiv.org"
    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(auth_req, service_url)

    req = urllib.request.Request(service_url + "/me")
    req.add_header("Authorization", f"Bearer {id_token}")
    response = urllib.request.urlopen(req)

"""
from contextlib import contextmanager
from threading import RLock
from typing import Union, Optional

import google.oauth2.id_token
import google.auth.transport.requests

import requests
import cachecontrol

_sess = None
"""Session with caching. 
See https://google-auth.readthedocs.io/en/stable/reference/google.oauth2.id_token.html
"""

_lock = RLock()
"""Lock for using the session. It doens't seem to be thread safe"""

@contextmanager
def locked_session():
    """Get a session with caching of certs from Google""" 
    global _sess
    with _lock:
        if not _sess:
            _sess = cachecontrol.CacheControl(requests.session())
        yield _sess
    
def verify_token(audience: str, token: Union[str,bytes]) -> Optional[dict]:
    """Call out to GCP to verify a JWT token."""
    with locked_session() as session:
        request = google.auth.transport.requests.Request(session=session)
        idinfo = google.oauth2.id_token.verify_oauth2_token(token, request, audience)
        if not idinfo:
            return None
        else:
            return idinfo

def email_from_idinfo(idinfo) -> Optional[str]:
    return idinfo.get('azp',None)
