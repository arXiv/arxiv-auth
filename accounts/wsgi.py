"""Web Server Gateway Interface entry-point."""

import os

__flask_app__ = None

def application(environ, start_response):    # type: ignore
    """WSGI application."""
    for key, value in environ.items():
        # In some deployment scenarios (e.g. uWSGI on k8s), uWSGI will pass in
        # the hostname as part of the request environ. This will usually just
        # be a container ID, which is not helpful for things like building
        # URLs. We want to keep ``SERVER_NAME`` explicitly configured, either
        # in config.py or via an os.environ var loaded by config.py.
        if key == 'SERVER_NAME':
            continue
        try:
            os.environ[key] = str(value)
        except UnicodeEncodeError as uee:
            print(f"{__file__} Could not decode bytes '{value}' for '{key}' most likely due to a surrogate. {uee}")

    global __flask_app__
    if __flask_app__ is None:
        from accounts.factory import create_web_app
        __flask_app__ = create_web_app()
    return __flask_app__(environ, start_response)
