"""Shared functions across arXiv projects."""

from typing import Any
from flask import url_for as flask_url_for


def url_for(endpoint: str, **values: dict) -> Any:
    """
    Build an URL for an ``endpoint``.

    Tries Flask first, then falls back to...
    """
    try:
        return flask_url_for(endpoint, **values)
    except RuntimeError as e:
        return endpoint
