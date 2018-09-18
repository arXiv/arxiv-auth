"""Create all tables in the registry database."""

from registry.factory import create_web_app
from registry.services import datastore

app = create_web_app()
datastore.init_app(app)
with app.app_context():
    datastore.create_all()
