"""Provides application for development purposes."""

from registry.factory import create_web_app
from registry.services import datastore

app = create_web_app()
with app.app_context():
    datastore.create_all()
