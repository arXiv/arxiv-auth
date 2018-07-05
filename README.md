[![Build Status](https://img.shields.io/travis/cul-it/arxiv-accounts/master.svg)](https://travis-ci.org/cul-it/arxiv-accounts) [![Coverage Status](https://img.shields.io/coveralls/github/cul-it/arxiv-accounts/master.svg)](https://coveralls.io/github/cul-it/arxiv-accounts?branch=master)

# arXiv Accounts

The arXiv platform provides both anonymous and authenticated interfaces to
end-users (including moderators), API clients, and the arXiv operations team.
This project provides applications and libraries to support authentication and
authorization, including account creation and login, user sessions, and API
token management.

There are currently three pieces of software in this repository:

1. [``users/``](users/) contains the ``arxiv.users`` package, which provides
   core authentication and authorization functionality and domain classes.
   This includes integrations with the legacy database for user accounts and
   sessions.
2. [``accounts/``](accounts/) contains the user accounts service, which
   provides the main UIs for registration, login/logout, profile management,
   etc.
3. [``authorizer/``](authorizer/) contains the authorizer service, which
   handles authorization requests from NGINX in a cloud deployment scenario.
   This is currently not ready for use nor evaluation.

TLS is considered an infrastructure concern, and is therefore out of scope
(albeit critical) for this project.

## TODO

- Password reset in ``arxiv.users.legacy.accounts`` and in the accounts
  service.
- Support for permanent login token.
- Clean up and document authorizer service.
- Fuzz testing registration?

## Dependencies

We use pipenv to manage dependencies. To install the dependencies for this
project, run ``pipenv install`` in the root of this repository.

Note that the ``Pipfile`` does not contain a reference to the ``arxiv.users``
package, which is located in ``users/``. To test against the code in your
current branch, install the package directly with ``pipenv install ./users``.
Otherwise, you can install the latest release with
``pipenv install arxiv-users``.

## Testing

Each of the applications/packages in this repository has its own test suite.

You can run everything together with:

```bash
pipenv run pytest \
    --cov=accounts \
    --cov=users/arxiv \
    --cov-report=term-missing \
    accounts users/arxiv
```

To enable integration + end-to-end tests with Redis, run:

```bash
WITH_INTEGRATION=1 pipenv run pytest \
    --cov=accounts \
    --cov=users/arxiv \
    --cov-report=term-missing \
    accounts users/arxiv
```

Note that this requires Docker to be running, and port 6379 to be free on your
machine.


### ``arxiv.users``

You can run the tests for the ``arxiv.users`` package with:

```bash
pipenv run pytest --cov=users/arxiv --cov-report=term-missing users/arxiv
```

### Accounts service

Note that in order to run the accounts service, you will need to install
``arxiv.users`` (not included in the Pipfile). See
[#dependencies](dependencies), above.

You can run tests for the accounts service with:

```bash
pipenv run pytest --cov=accounts --cov-report=term-missing accounts
```

To run integration and end-to-end tests with a live Redis, use:

```bash
WITH_INTEGRATION=1 pipenv run pytest --cov=accounts --cov-report=term-missing accounts
```

Note that this requires Docker to be running, and port 6379 to be free on your
machine.


## Local development + manual testing

You can start the accounts service in a manner similar to other Flask apps.
You will need to run Redis, which is most easily achieved using Docker:

```bash
docker run -it -p 6379:6379 redis:latest
```

This will start a local Redis instance, and map your host port 6379 to the
Redis instance.

To start the application itself, first make sure that all dependencies are
installed. You'll need to install the ``arxiv.users`` package; see
[#dependencies](dependencies).

We assume your developer machine already has a version of Python 3.6
with `pip`.

```bash
pipenv install --dev
FLASK_APP=app.py FLASK_DEBUG=1 pipenv run flask run
```

You should be able to register a new user at
http://localhost:5000/user/register.

## Code style

All new code should adhere as closely as possible to
[PEP008](https://www.python.org/dev/peps/pep-0008/).

Use the [Numpy style](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt)
for docstrings.

### Linting

Use [Pylint](https://www.pylint.org/) to check your code prior to raising a
pull request. The parameters below will be used when checking code  cleanliness
on commits, PRs, and tags, with a target score of >= 9/10.

If you're using Atom as your text editor, consider using the
[linter-pylama](https://atom.io/packages/linter-pylama) package for real-time
feedback.

Here's how we use pylint in CI:

```bash
$ pipenv run pylint accounts/accounts users/arxiv/users
************* Module accounts.context
accounts/context.py:10: [W0212(protected-access), get_application_config] Access to a protected member _Environ of a client class
************* Module accounts.encode
accounts/encode.py:11: [E0202(method-hidden), ISO8601JSONEncoder.default] An attribute defined in json.encoder line 158 hides this method
************* Module accounts.controllers.baz
accounts/controllers/baz.py:1: [C0102(blacklisted-name), ] Black listed name "baz"
************* Module accounts.services.baz
accounts/services/baz.py:1: [C0102(blacklisted-name), ] Black listed name "baz"
************* Module accounts.services.things
accounts/services/things.py:11: [R0903(too-few-public-methods), Thing] Too few public methods (0/2)
accounts/services/things.py:49: [E1101(no-member), get_a_thing] Instance of 'scoped_session' has no 'query' member

------------------------------------------------------------------
Your code has been rated at 9.49/10 (previous run: 9.41/10, +0.07)
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

Point your browser to: ``file:///path/to/arxiv-accounts/docs/build/html/index.html``.

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
rm -rf docs/source/arxiv.users
sphinx-apidoc -o docs/source/arxiv.users -e -f -M --implicit-namespaces users/arxiv *test*/*
rfm -rf docs/source/accounts
sphinx-apidoc -o docs/source/accounts -e -f -M accounts *test*/*
```
