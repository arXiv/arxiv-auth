"""
Helper script for generating an auth JWT.

Be sure that you are using the same secret when running this script as when you
run the app. Set ``JWT_SECRET=somesecret`` in your environment to ensure that
the same secret is always used.


.. code-block:: bash

   $ JWT_SECRET=foosecret pipenv run python generate_token.py
   Numeric user ID: 4
   Email address: joe@bloggs.com
   Username: jbloggs1
   First name [Jane]: Joe
   Last name [Doe]: Bloggs
   Name suffix [IV]:
   Affiliation [Cornell University]:
   Numeric rank [3]:
   Alpha-2 country code [us]:
   Default category [astro-ph.GA]:
   Submission groups (comma delim) [grp_physics]:
   Endorsement categories (comma delim) [astro-ph.CO,astro-ph.GA]:
   Authorization scope (comma delim) [upload:read,upload:write,upload:admin]:

   eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiZTljMGQwMDUtMTk1My00YWRiLWE0YzEtYzdmNWY1OGM5YTk4Iiwic3RhcnRfdGltZSI6IjIwMTgtMDgtMDlUMTQ6NDg6MDguNzY2NjUzLTA0OjAwIiwidXNlciI6eyJ1c2VybmFtZSI6ImVyaWNrIiwiZW1haWwiOiJlcmlja0Bmb28uY29tIiwidXNlcl9pZCI6IjQiLCJuYW1lIjp7ImZvcmVuYW1lIjoiSmFuZSIsInN1cm5hbWUiOiJEb2UiLCJzdWZmaXgiOiJJViJ9LCJwcm9maWxlIjp7ImFmZmlsaWF0aW9uIjoiQ29ybmVsbCBVbml2ZXJzaXR5IiwiY291bnRyeSI6InVzIiwicmFuayI6Mywic3VibWlzc2lvbl9ncm91cHMiOlsiZ3JwX3BoeXNpY3MiXSwiZGVmYXVsdF9jYXRlZ29yeSI6eyJhcmNoaXZlIjoiYXN0cm8tcGgiLCJzdWJqZWN0IjoiR0EifSwiaG9tZXBhZ2VfdXJsIjoiIiwicmVtZW1iZXJfbWUiOnRydWV9fSwiY2xpZW50IjpudWxsLCJlbmRfdGltZSI6IjIwMTgtMDgtMTBUMDA6NDg6MDguNzY2NjUzLTA0OjAwIiwiYXV0aG9yaXphdGlvbnMiOnsiY2xhc3NpYyI6MCwiZW5kb3JzZW1lbnRzIjpbW1siYXN0cm8tcGgiLCJDTyJdLG51bGxdLFtbImFzdHJvLXBoIiwiR0EiXSxudWxsXV0sInNjb3BlcyI6W1sidXBsb2FkOnJlYWQiLCJ1cGxvYWQ6d3JpdGUiLCJ1cGxvYWQ6YWRtaW4iXV19LCJpcF9hZGRyZXNzIjpudWxsLCJyZW1vdGVfaG9zdCI6bnVsbCwibm9uY2UiOm51bGx9.aOgRj73TT-zsRvF7gnPPjplJzcnXkKzYzEvMB61jEsY


Start the dev server with:

.. code-block:: bash

   $ JWT_SECRET=foosecret FLASK_APP=app.py FLASK_DEBUG=1 pipenv run flask run


Use the (rather long) token in your requests to authorized endpoints. Set the
header ``Authorization: [token]``.  There are apps that will do this for you.
For Chrome, try `Requestly <https://chrome.google.com/webstore/detail/requestly-redirect-url-mo/mdnleldcmiljblolnjhpnblkcekpdkpa?hl=en>`_
or `ModHeader <https://chrome.google.com/webstore/detail/modheader/idgpnmonknjnojddfkpgkljpfnnfcklj?hl=en>`_.

"""

import click

import os
from pytz import timezone
import uuid
from datetime import timedelta, datetime
from arxiv.users import auth, domain

DEFAULT_SCOPES = " ".join(([
    "public:read",
    "submission:create",
    "submission:update",
    "submission:read",
    "upload:create",
    "upload:update",
    "upload:read",
    "upload:delete",
    "upload:read_logs"
]))


@click.command()
@click.option('--user_id', prompt='Numeric user ID')
@click.option('--email', prompt='Email address')
@click.option('--username', prompt='Username')
@click.option('--first_name', prompt='First name', default='Jane')
@click.option('--last_name', prompt='Last name', default='Doe')
@click.option('--suffix_name', prompt='Name suffix', default='IV')
@click.option('--affiliation', prompt='Affiliation',
              default='Cornell University')
@click.option('--rank', prompt='Numeric rank', default=3)
@click.option('--country', prompt='Alpha-2 country code', default='us')
@click.option('--default_category', prompt='Default category',
              default='astro-ph.GA')
@click.option('--submission_groups', prompt='Submission groups (comma delim)',
              default='grp_physics')
@click.option('--endorsements', prompt='Endorsement categories (comma delim)',
              default='astro-ph.CO,astro-ph.GA')
@click.option('--scope', prompt='Authorization scope (space delim)',
              default=DEFAULT_SCOPES)
def generate_token(user_id: str, email: str, username: str,
                   first_name: str = 'Jane', last_name: str = 'Doe',
                   suffix_name: str = 'IV',
                   affiliation: str = 'Cornell University',
                   rank: int = 3,
                   country: str = 'us',
                   default_category: str = 'astro-ph.GA',
                   submission_groups: str = 'grp_physics',
                   endorsements: str = 'astro-ph.CO,astro-ph.GA',
                   scope: str = DEFAULT_SCOPES) \
        -> None:
    """Generate an auth token for dev/testing purposes."""
    # Specify the validity period for the session.
    start = datetime.now(tz=timezone('US/Eastern'))
    end = start + timedelta(seconds=36000)   # Make this as long as you want.

    # Create a user with endorsements in astro-ph.CO and .GA.
    session = domain.Session(
        session_id=str(uuid.uuid4()),
        start_time=start, end_time=end,
        user=domain.User(
            user_id=user_id,
            email=email,
            username=username,
            name=domain.UserFullName(first_name, last_name, suffix_name),
            profile=domain.UserProfile(
                affiliation=affiliation,
                rank=int(rank),
                country=country,
                default_category=domain.Category(
                    *default_category.split('.', 1)
                ),
                submission_groups=submission_groups.split(',')
            )
        ),
        authorizations=domain.Authorizations(
            scopes=[domain.Scope(*s.split(':')) for s in scope.split()],
            endorsements=[domain.Category(*cat.split('.', 1))
                          for cat in endorsements.split(',')]
        )
    )
    token = auth.tokens.encode(session, os.environ['JWT_SECRET'])
    click.echo(token)


if __name__ == '__main__':
    generate_token()
