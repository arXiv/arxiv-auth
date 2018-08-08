from flask import Flask, jsonify, make_response
from werkzeug.exceptions import BadRequest, NotFound, BadRequest, Forbidden, \
    Unauthorized
from arxiv.base import Base
from . import routes


def jsonify_exception(error):
    exc_resp = error.get_response()
    response = jsonify(reason=error.description)
    response.status_code = exc_resp.status_code
    return response


def create_app() -> Flask:
    """Initialize an instance of the authenticator service."""
    app = Flask('authenticator')
    app.config.from_pyfile('config.py')

    app.register_blueprint(routes.blueprint)
    app.errorhandler(NotFound)(jsonify_exception)
    app.errorhandler(BadRequest)(jsonify_exception)
    app.errorhandler(Unauthorized)(jsonify_exception)
    app.errorhandler(Forbidden)(jsonify_exception)
    return app
