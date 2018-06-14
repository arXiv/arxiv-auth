from flask import Flask, jsonify, make_response
from werkzeug.exceptions import BadRequest, NotFound, BadRequest
from . import routes


def jsonify_exception(error):
    exc_resp = error.get_response()
    response = jsonify(reason=error.description)
    response.status_code = exc_resp.status_code
    return response


def create_app() -> Flask:
    """Initialize an instance of the extractor backend service."""
    app = Flask('authorizer')
    app.config.from_pyfile('config.py')

    app.register_blueprint(routes.blueprint)
    app.errorhandler(NotFound)(jsonify_exception)
    app.errorhandler(BadRequest)(jsonify_exception)
    app.errorhandler(BadRequest)(jsonify_exception)
    return app
