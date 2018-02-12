"""Provides routes for the external API."""

from flask.json import jsonify
from flask import Blueprint, render_template, redirect, request, url_for
from accounts import status, authorization
from accounts.controllers import baz, things

blueprint = Blueprint('external_api', __name__, url_prefix='/accounts/api')


@blueprint.route('/status', methods=['GET'])
def ok() -> tuple:
    """Health check endpoint."""
    return jsonify({'status': 'nobody but us hamsters'}), status.HTTP_200_OK


@blueprint.route('/baz/<int:baz_id>', methods=['GET'])
def read_baz(baz_id: int) -> tuple:
    """Provide some data about the baz."""
    data, status_code, headers = baz.get_baz(baz_id)
    return jsonify(data), status_code, headers


@blueprint.route('/thing/<int:thing_id>', methods=['GET'])
@authorization.scoped('read:thing')
def read_thing(thing_id: int) -> tuple:
    """Provide some data about the thing."""
    data, status_code, headers = things.get_thing(thing_id)
    return jsonify(data), status_code, headers


@blueprint.route('/thing', methods=['POST'])
@authorization.scoped('write:thing')
def create_thing() -> tuple:
    """Create a new thing."""
    payload = request.get_json(force=True)    # Ignore Content-Type header.
    data, status_code, headers = things.create_a_thing(payload)
    return jsonify(data), status_code, headers


@blueprint.route('/thing/<int:thing_id>', methods=['POST'])
@authorization.scoped('write:thing')
def mutate_thing(thing_id: int) -> tuple:
    """Request that the thing be mutated."""
    data, status_code, headers = things.start_mutating_a_thing(thing_id)
    return jsonify(data), status_code, headers


@blueprint.route('/mutation/<string:task_id>', methods=['GET'])
@authorization.scoped('write:thing')
def mutation_status(task_id: str) -> tuple:
    """Get the status of the mutation task."""
    data, status_code, headers = things.mutation_status(task_id)
    return jsonify(data), status_code, headers
