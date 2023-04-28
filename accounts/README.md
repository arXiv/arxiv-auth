# `accounts`
The [``accounts/``](accounts/) directory contains a flask web app for
the `/login` `/logout` and other pages.


```bash
cd accounts/
pip install poetry
poetry install  # installs to a venv
poetry shell    # activates the venv
pytest
REDIS_FAKE=1 CLASSIC_DATABASE_URI=sqlite:///my.db CREATE_DB=1 python main.py
google-chrome http://localhost:5000/login
```

## Local development + manual testing

You can start the accounts service in a manner similar to other Flask apps. You
will need to run Redis or configure to use a fake redis

If using Redis, you'll need to start a local Redis instance, and map your host
port 7000-7006 to the Redis instance. We're running Redis in cluster mode; the
image used in this example is for dev/test purposes only.

You will also need to decide what you want to use for the legacy user
and session database backend. For local development/testing purposes,
it's fine to use an on-disk SQLite database. You should also be able
to use a local MySQL instance with a clone of the legacy database.

If you are starting with SQLite and don't already have a DB with users in it,
you can use the ``accounts/create_user.py`` script. Note that this is for local
dev/testing purposes only, and should never be used on a production DB ever
under any circumstances with no exceptions.

```bash
docker run -d \
 -p 7000:7000 -p 7001:7001 -p 7002:7002 -p 7003:7003 -p 7004:7004 -p 7005:7005 -p 7006:7006 \
 -e "IP=0.0.0.0" --hostname=server grokzen/redis-cluster:4.0.9

poetry install
poetry shell

CLASSIC_DATABASE_URI=sqlite:///my.db FLASK_APP=main.py FLASK_DEBUG=1 \
 python accounts/create_user.py
```

You should be prompted to enter some profile details. Note that this currently
selects your default category and groups at random.

Then start the Flask dev server with:

```bash
CLASSIC_DATABASE_URI=sqlite:///my.db python main.py
```

To use MySQL/MariaDB:

```bash
poetry shell
CLASSIC_DATABASE_URI=mysql+mysqldb://[USERNAME]:[PASSWORD]@localhost:3306/[DATABASE] \
 python main.py
```

Set the username, password, and database to whatever you're using. If
the DB structure does not already exist, you will need to be able to
create tables. Conventional read/write access should be sufficient.

## Need to reinstall arxiv-auth
If you are doing local development and make a change to arxiv-auth and want have
that change in `accounts` you will need to reinstall `arxiv-auth` by running
`poetry install`. Flask's auto-restart of the service in debug mod will not pick
up changes to `arxiv-auth`.

## TODO
- Password reset in ``arxiv.users.legacy.accounts`` and in the accounts service.
- Investigate the state of the accounts user registration and clean up, test and
  document if useful.

## Generating auth tokens

Use the helper script ``generate_token.py`` to generate auth tokens for
dev/testing purposes.

Be sure that you are using the same secret when running this script as when you
run the app. Set ``JWT_SECRET=somesecret`` in your environment to ensure that
the same secret is always used.

```bash
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
```

Start the dev server with:

```bash
$ JWT_SECRET=foosecret FLASK_APP=main.py FLASK_DEBUG=1 pipenv run flask run
```

Use the (rather long) token in your requests to authorized endpoints. Set the
header ``Authorization: [token]``. There are apps that will do this for you.
For Chrome, try [Requestly](https://chrome.google.com/webstore/detail/requestly-redirect-url-mo/mdnleldcmiljblolnjhpnblkcekpdkpa?hl=en>) or [ModHeader](https://chrome.google.com/webstore/detail/modheader/idgpnmonknjnojddfkpgkljpfnnfcklj?hl=en
)
