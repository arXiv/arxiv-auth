"""Helper script to initialize the Thing database and add a few rows."""

from datetime import datetime
import click
from accounts.factory import create_web_app
from accounts.services import things

app = create_web_app()
app.app_context().push()


@app.cli.command()
def populate_database():
    """Initialize the search index."""
    things.db.create_all()
    things.db.session.add(things.DBThing(name='The first thing', created=datetime.now()))
    things.db.session.add(things.DBThing(name='The second thing', created=datetime.now()))
    things.db.session.add(things.DBThing(name='The third thing', created=datetime.now()))
    things.db.session.commit()


if __name__ == '__main__':
    populate_database()
