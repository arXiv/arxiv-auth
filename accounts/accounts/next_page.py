"""Next page handling."""
import re

from accounts import config

def good_next_page(next_page: str) -> str:
    """Checks if a next_page is good and returns it.

    If not good, it will return the default.
    """
    good = (next_page and len(next_page) < 300 and
            (next_page == config.DEFAULT_LOGIN_REDIRECT_URL
             or re.match(config.login_redirect_pattern, next_page))
            )
    return next_page if good else config.DEFAULT_LOGIN_REDIRECT_URL
