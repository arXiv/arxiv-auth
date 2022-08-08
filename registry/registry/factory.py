"""Application factory for client registry app."""

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException, Forbidden, Unauthorized, \
    BadRequest, MethodNotAllowed, InternalServerError, NotFound

from arxiv.base import Base
from arxiv.base.middleware import wrap
from arxiv.users import auth
from arxiv.users.auth.middleware import AuthMiddleware

# from registry.routes import ui
from registry import filters
from registry.services import datastore, SessionStore
from registry.routes import blueprint
from . import oauth2


def create_web_app() -> Flask:
    """Initialize and configure the accounts application."""
    app = Flask('registry')
    app.config.from_pyfile('config.py')

    # app.register_blueprint(ui.blueprint)

    datastore.init_app(app)
    SessionStore.init_app(app)

    Base(app)    # Gives us access to the base UI templates and resources.
    auth.Auth(app)  # Handless sessions and authn/z.
    oauth2.init_app(app)
    app.register_blueprint(blueprint)

    middleware = [AuthMiddleware]
    wrap(app, middleware)

    app.jinja_env.filters['scope_label'] = filters.scope_label

    if app.config['CREATE_DB']:
        with app.app_context():
            datastore.create_all()

    register_error_handlers(app)
    return app


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask app."""
    app.errorhandler(Forbidden)(jsonify_exception)
    app.errorhandler(Unauthorized)(jsonify_exception)
    app.errorhandler(BadRequest)(jsonify_exception)
    app.errorhandler(InternalServerError)(jsonify_exception)
    app.errorhandler(NotFound)(jsonify_exception)
    app.errorhandler(MethodNotAllowed)(jsonify_exception)


def jsonify_exception(error: HTTPException) -> Response:
    """Render exceptions as JSON."""
    exc_resp = error.get_response()
    response: Response = jsonify(reason=error.description)
    response.status_code = exc_resp.status_code
    return response
