"""Web Server Gateway Interface entry-point."""

from accounts.factory import create_web_app
import os
import logging

__flask_app__ = None

def application(environ, start_response):    # type: ignore
    """WSGI application."""

    logging.error("THIS IS A ERROR from arxiv-auth that we should see in http's error log!")

    # print("PID: %s" % os.getpid(), file=environ['wsgi.errors'])
    # print("UID: %s" % os.getuid(), file=environ['wsgi.errors'])
    # print("GID: %s" % os.getgid(), file=environ['wsgi.errors'])


    # print("******** wsgi environ *******", file=environ['wsgi.errors'])
    # keys = environ.keys()
    # #keys.sort()
    # for key in keys:
    #     print('%s: %s' % (key, repr(environ[key])), file=environ['wsgi.errors'])

    # print("******** os environ before changes *******", file=environ['wsgi.errors'])
    # keys = os.environ.keys()
    # #keys.sort()
    # for key in keys:
    #     print('%s: %s' % (key, repr(os.environ[key])), file=environ['wsgi.errors'])


    for key, value in environ.items():
        # In some deployment scenarios (e.g. uWSGI on k8s), uWSGI will pass in
        # the hostname as part of the request environ. This will usually just
        # be a container ID, which is not helpful for things like building
        # URLs. We want to keep ``SERVER_NAME`` explicitly configured, either
        # in config.py or via an os.environ var loaded by config.py.
        if key == 'SERVER_NAME':
            continue
        os.environ[key] = str(value)


    print("******** os environ after changes *******", file=environ['wsgi.errors'])
    keys = os.environ.keys()
    #keys.sort()
    for key in keys:
        print('%s: %s' % (key, repr(os.environ[key])), file=environ['wsgi.errors'])


    global __flask_app__
    if __flask_app__ is None:
        __flask_app__ = create_web_app()
    return __flask_app__(environ, start_response)
