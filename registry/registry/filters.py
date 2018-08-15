"""Jinja2 template filters."""

from arxiv.users import auth
from flask import Markup


def scope_label(scope: str) -> str:
    """Get the description of an auth scope from the docstring."""
    return Markup(auth.scopes.get_human_label(scope))
