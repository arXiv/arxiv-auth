"""Provides application for development purposes."""

from accounts.factory import create_web_app
from accounts.services import classic_session_store, user_data

app = create_web_app()
with app.app_context():
    classic_session_store.create_all()
    user_data.create_all()
