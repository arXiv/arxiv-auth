import socket
import logging
from typing import Tuple, Optional

from arxiv.auth.user_claims import ArxivUserClaims
from arxiv.auth.user_claims_to_legacy import create_tapir_session_from_user_claims
from arxiv.auth.domain import Session as ArxivSession
from arxiv.auth.legacy.exceptions import NoSuchUser, SessionCreationFailed

logger = logging.getLogger(__name__)

def create_tapir_session(
        user_claims: ArxivUserClaims, client_ip: str
) -> Tuple[Optional[str], Optional[ArxivSession]]:
    # legacy cookie
    client_host = ''
    logger.info("User claims: ip=%s", client_ip)
    try:
        client_host = socket.gethostbyaddr(client_ip)[0]
    except Exception as _exc:
        logger.info('client host resolve failed for ip %s', client_ip)
        pass

    tapir_cookie = None
    tapir_session = None
    try:
        ts = create_tapir_session_from_user_claims(user_claims, client_host, client_ip)
        if ts:
            tapir_cookie = ts[0]
            tapir_session = ts[1]
    except NoSuchUser:
        # Likely the user exist on keycloak but not in tapir user.
        # Since newer apps should work without
        logger.info("User exists on keycloak but not on tapir", exc_info=False)
        return (None, None)

    except SessionCreationFailed:
        logger.error("Tapir session creation", exc_info=True)
        return (None, None)

    except Exception as _exc:
        logger.error("Setting up Tapir session failed.", exc_info=True)
        return (None, None)

    if tapir_session is not None:
        logger.debug("tapir_session: %s", repr(tapir_session))
    return tapir_cookie, tapir_session
