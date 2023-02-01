# arXiv Auth and accounts

This project provides applications and libraries to support
authentication and authorization, including login, user sessions, and
API token management.

There are currently four pieces of software in this repository:

1. [``users/``](users/) contains the ``arxiv.users`` package, which provides
   core authentication and authorization functionality and domain classes.
   This includes integrations with the legacy database for user accounts and
   sessions.
2. [``accounts/``](accounts/) contains the user accounts service, which
   provides the main UIs for registration, /login, /logout, /user, etc. 
   Only login, logout and the user page are currently in use.
3. [``authenticator/``](authenticator/) contains the authenticator service.
   Handles authentication requests from NGINX in a cloud deployment scenario.
   *This is NOT in use in production.*
4. [``registry/``](registry/) contains the API client registry application.
   This implements OAuth2 workflows, client registration, and the root API
   landing page. *This is NOT in use in production.*

# Testing

```bash
pyenv install 3.6.2
pyenv virtualenv 3.6.2 arxiv-auth 
pip install pipenv==2021.5.29
pipenv sync -d
pipenv run pytest \
    --cov=accounts \
    --cov=users/arxiv \
    --cov-report=term-missing \
    accounts users/arxiv
```

Run this to enable integration + end-to-end tests with Redis, (which requires
Docker to be running and port 7000 to be free on your machine):

```bash
WITH_INTEGRATION=1 pipenv run pytest \
    --cov=accounts \
    --cov=users/arxiv \
    --cov-report=term-missing \
    accounts users/arxiv
```

## Local development + manual testing

You can start the accounts service in a manner similar to other Flask apps.
You will need to run Redis, which is most easily achieved using Docker:

```bash
docker run -d \
 -p 7000:7000 -p 7001:7001 -p 7002:7002 -p 7003:7003 -p 7004:7004 -p 7005:7005 -p 7006:7006 \
 -e "IP=0.0.0.0" --hostname=server grokzen/redis-cluster:4.0.9
```

This will start a local Redis instance, and map your host port 7000-7006 to the
Redis instance.

Note: we're running Redis in cluster mode; the image used in this example
is for dev/test purposes only.

To start the application itself, first make sure that all dependencies are
installed. You'll need to install the ``arxiv.users`` package; see
[#dependencies](dependencies).

```bash
pipenv install --dev
```

You will also need to decide what you want to use for the legacy user and
session database backend. For local development/testing purposes, it's fine to
use an on-disk SQLite database. You should also be able to use a local MySQL
instance with a clone of the legacy database.

If you are starting with SQLite and don't already have a DB with users in it,
you can use the ``accounts/create_user.py`` script. Note that this is for local
dev/testing purposes only, and should never be used on a production DB ever
under any circumstances with no exceptions.

```bash
CLASSIC_DATABASE_URI=sqlite:///my.db FLASK_APP=app.py FLASK_DEBUG=1 pipenv run python create_user.py
```

You should be prompted to enter some profile details. Note that this currently
selects your default category and groups at random.

Then start the Flask dev server with:

```bash
CLASSIC_DATABASE_URI=sqlite:///my.db FLASK_APP=app.py FLASK_DEBUG=1 pipenv run flask run
```

To use MySQL/MariaDB:

```bash
CLASSIC_DATABASE_URI=mysql+mysqldb://[USERNAME]:[PASSWORD]@localhost:3306/[DATABASE] \
 FLASK_APP=app.py FLASK_DEBUG=1 pipenv run flask run
```

Set the username, password, and database to whatever you're using. If the DB
structure does not already exist, the user will need to be able to create
tables. Otherwise conventional read/write access should be sufficient.

You should be able to register a new user at
http://localhost:5000/register.

## Dependencies
We use pipenv to manage dependencies. To install the dependencies for this
project, run ``pipenv install`` in the root of this repository.

Note that the ``Pipfile`` does not contain a reference to the ``arxiv.users``
package, which is located in ``users/``. To test against the code in your
current branch, install the package directly with ``pipenv install ./users``.
Otherwise, you can install the latest release with
``pipenv install arxiv-users``.

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

eyJ0e(~900 chars omited)1jEsY
```


Start the dev server with:

```bash
$ JWT_SECRET=foosecret FLASK_APP=app.py FLASK_DEBUG=1 pipenv run flask run
```


Use the (rather long) token in your requests to authorized endpoints. Set the
header ``Authorization: [token]``.  There are apps that will do this for you.
For Chrome, try [Requestly](https://chrome.google.com/webstore/detail/requestly-redirect-url-mo/mdnleldcmiljblolnjhpnblkcekpdkpa?hl=en>)
or
[ModHeader](https://chrome.google.com/webstore/detail/modheader/idgpnmonknjnojddfkpgkljpfnnfcklj?hl=en)

## Code style

All new code should adhere as closely as possible to
[PEP008](https://www.python.org/dev/peps/pep-0008/).

Use the [Numpy style](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt)
for docstrings.

### Linting

Use [Pylint](https://www.pylint.org/) to check your code prior to raising a
pull request. The parameters below will be used when checking code  cleanliness
on commits, PRs, and tags, with a target score of >= 9/10.

Here's how we use pylint in CI or from the command line:

```bash
$ pipenv run pylint accounts/accounts users/arxiv/users
```

### Docstyle
To verify the documentation style, use the tool
[PyDocStyle](http://www.pydocstyle.org/en/2.1.1/)

Here's how we run pydocstyle in CI:

```bash
pipenv run pydocstyle --convention=numpy --add-ignore=D401 accounts users/arxiv
```

## Type hints and static checking
Use [type hint annotations](https://docs.python.org/3/library/typing.html)
wherever practicable. Use [mypy](http://mypy-lang.org/) to check your code.
If you run across typechecking errors in your code and you have a good reason
for `mypy` to ignore them, you should be able to add `# type: ignore`,
ideally along with an actual comment describing why the type checking should be
ignored on this line. In cases where it is hoped the types can be specified later,
just simplying adding the `# type: ignore` without further comment is fine.


Try running mypy with (from project root):

```bash
pipenv run mypy accounts users/arxiv | grep -v "test.*" | grep -v "defined here"
```

Mypy options are most easily specified by adding them to `mypy.ini` in the repo's
root directory.

mypy chokes on dynamic base classes and proxy objects (which you're likely
to encounter using Flask); it's perfectly fine to disable checking on those
offending lines using "``# type: ignore``". For example:

```python
>>> g.baz = get_session(app) # type: ignore
```

See [this issue](https://github.com/python/mypy/issues/500) for more
information.

## Documentation

Documentation is built with [Sphinx](http://www.sphinx-doc.org/en/stable/rest.html).
The documentation source files (in [reST markdown](http://www.sphinx-doc.org/en/stable/rest.html))
are in ``docs/source``. Everything in that directory **is** under version
control. The rendered documentation is located in ``docs/build``; those files
are **not** under version control (per ``.gitignore``).

To build the full documentation for this project:

```bash
cd <project_root>/docs
make html SPHINXBUILD=$(pipenv --venv)/bin/sphinx-build
```

Point your browser to: ``file:///path/to/arxiv-auth/docs/build/html/index.html``.

There are other build targets available. Run ``make`` without any arguments
for more info.

### Architecture

Architectural documentation is located at
[``docs/source/architecture.rst``](docs/source/architecture.rst). This can be
exploded into multiple files, if necessary.

This architecture documentation is based on the [arc42](http://arc42.org/)
documentation model, and also draws heavily on the [C4 software architecture
model](https://www.structurizr.com/help/c4>). The C4 model describes an
architecture at four hierarchical levels, from the business context of the
system to the internal architecture of small parts of the system.

In document for arXiv NG services, we have departed slightly from the original
language of C4 in order to avoid collision with names in adjacent domains.
Specifically, we describe the system at three levels:

1. **Context**: This includes both the business and technical contexts in the
   arc42 model. It describes the interactions between a service and
   other services and systems.
2. **Building block**: This is similar to the "container" concept in the C4
   model. A building block is a part of the system that is developed, tested,
   and deployed quasi-independently. This might be a single application, or
   a data store.
3. **Component**: A component is an internal part of a building block. In the
   case of a Flask application, this might be a module or submodule that has
   specific responsibilities, behaviors, and interactions.

### Code API documentation

Documentation for the (code) API is generated automatically with
[sphinx-apidoc](http://www.sphinx-doc.org/en/stable/man/sphinx-apidoc.html),
and lives in ``docs/source/api``.

sphinx-apidoc generates references to modules in the code, which are followed
at build time to retrieve docstrings and other details. This means that you
won't need to run sphinx-apidoc unless the structure of the project changes
(e.g. you add/rename a module).

To rebuild the API docs, run (from the project root):

```bash
sphinx-apidoc -o docs/source/arxiv.users -e -f -M --implicit-namespaces users/arxiv *test*/*
sphinx-apidoc -o docs/source/accounts -e -f -M accounts *test*/*
```
