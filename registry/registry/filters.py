"""Jinja2 template filters."""


def scope_definition(scope: str) -> str:
    """Get the description of an auth scope from the docstring."""
    return scope.__doc__
