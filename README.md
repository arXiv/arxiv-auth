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

TLS is considered an infrastructure concern, and is therefore out of scope
(albeit critical) for this project.

## Documentation

Documentation source files can be found in ``docs``

sphinx-apidoc -o docs/source/arxiv.users -e -f -M --implicit-namespaces users/arxiv *test*/*
sphinx-apidoc -o docs/source/accounts -e -f -M accounts *test*/*


## Quick start

There are multiple ways to run this server:

### Docker

1.  Setup [Docker CE using the instructions for your OS](https://docs.docker.com/engine/installation/)
2.  Build [arxiv-base](https://github.com/cul-it/arxiv-base)
(clone repo, then `docker build -t arxiv-base:latest .`) if not using a registry.
    Also note, if not using a registry, you may need to create the tag manually in some docker
    installations or versions: `docker tag built_image_id arxiv-base:latest` (seems to be a docker bug).
3.  Build the Docker image, which will execute all the commands in the
    [`Dockerfile`](https://github.com/cul-it/arxiv-accounts/blob/master/Dockerfile):
    `docker build -t arxiv-accounts .`
4.  `docker run -p 8000:8000 --name container_name arxiv-accounts` (add a `-d` flag
    to run in daemon mode)
5.  Test that the container is working: http://localhost:8000/accounts/api/status
6.  To shut down the container: `docker stop container_name`
7.  Each time you change a file, you will need to rebuild the Docker image in
    order to import the updated files. Alternatively, volume-mount selected parts
    of your home directory such has .ssh and .gitconfig in your `docker run` command
    if you wish to be able to push modifications to github.

#### Clean-up

To purge your container run  `docker rmi arxiv-accounts`. If you receive the
following error, run `docker rm CONTAINER_ID` for each stopped container
until it clears:

```
$ docker rmi c196c3ef21c7
Error response from daemon: conflict: unable to delete c196c3ef21c7 (must be
forced) - image is being used by stopped container 75bb481b5857
```

### Local Deployment

Sometimes Docker adds more overhead than you want, especially when making quick
changes. We assume your developer machine already has a version of Python 3.6
with `pip`.

1.  `pip install pipenv && pipenv install --dev`
2.  `pipenv shell`
3.  `FLASK_APP=app.py python populate_test_database.py`
4.  `FLASK_APP=app.py FLASK_DEBUG=1 flask run`
5.  Test that the app is working: http://localhost:5000/accounts/api/status

#### Notes on the development server

Flask provides a single-threaded dev server for your enjoyment.

The entrypoint for this dev server is [``app.py``](app.py) (in the root of the
project). Flask expects the path to this entrypoint in the environment variable
``FLASK_APP``. To run the dev server, try (from the project root):

```bash
$ FLASK_APP=app.py FLASK_DEBUG=1 flask run
```

``FLASK_DEBUG=1`` enables a slew of lovely development and debugging features.
For example, the dev server automatically restarts when you make changes to the
application code.

Note that neither the dev server or the ``app.py`` entrypoint are acceptable
for use in production.

A convenience script [``populate_test_database.py``](populate_test_database.py)
is provided to set up an on-disk SQLite database and some sample data. You can
use this as a starting point for more complex set-up operations (or not). Be
sure to run this with the ``FLASK_APP`` variable set, e.g.

```bash
$ FLASK_APP=app.py python populate_test_database.py
```

## Testing

Some example unit tests are provided in [``tests/``](tests/). They are written
using the built-in [unit-test](https://docs.python.org/3/library/unittest.html)
framework. **Be sure to change** [``tests/test_mypy.py``](tests/test_mypy.py) to reference
your python package by change the line `self.pkgname: str = "accounts"` to have
your package name rather than "accounts".

We use the [nose2](http://nose2.readthedocs.io/en/latest/) test runner, with
coverage. For example:

```bash
$ nose2 --with-coverage
..............
----------------------------------------------------------------------
Ran 14 tests in 0.109s

OK
Name                                Stmts   Miss  Cover
-------------------------------------------------------
app.py                                  2      2     0%
populate_test_database.py              14     14     0%
tests/test_routes_external_api.py      40      4    90%
tests/test_routes_ui.py                24      0   100%
tests/test_service_foo.py              68      0   100%
tests/test_service_things.py           30      0   100%
wsgi.py                                 7      7     0%
accounts/__init__.py                        0      0   100%
accounts/authorization.py                  20      3    85%
accounts/config.py                         12      0   100%
accounts/context.py                        16      6    62%
accounts/controllers/__init__.py            0      0   100%
accounts/controllers/baz.py                13      4    69%
accounts/controllers/things.py             13      4    69%
accounts/encode.py                         12      5    58%
accounts/factory.py                        16      0   100%
accounts/logging.py                        16      3    81%
accounts/routes/__init__.py                 0      0   100%
accounts/routes/external_api.py            17      1    94%
accounts/routes/ui.py                      23      4    83%
accounts/services/__init__.py               1      0   100%
accounts/services/baz.py                   54     10    81%
accounts/services/things.py                20      0   100%
accounts/status.py                         45      0   100%
-------------------------------------------------------
TOTAL                                 463     67    86%
```

## Code style

All new code should adhere as closely as possible to
[PEP008](https://www.python.org/dev/peps/pep-0008/).

Use the [Numpy style](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt)
for docstrings.

### Linting

Use [Pylint](https://www.pylint.org/) to check your code prior to raising a
pull request. The parameters below will be used when checking code  cleanliness
on commits, PRs, and tags, with a target score of >= 9/10.

If you're using Atom as your text editor, consider using the [linter-pylama](https://atom.io/packages/linter-pylama)
package for real-time feedback.

```bash
$ pylint accounts
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

To verify the pylintrc matches the current flags:

```bash
$ diff .pylintrc <(pylint --disable=W0622,W0611,F0401,R0914,W0221,W0222,W0142,F0010,W0703,R0911,C0102,C0103,R0913 -f parseable --generate-rcfile)
```

### Docstyle
To verify the documentation style, use the tool [PyDocStyle](http://www.pydocstyle.org/en/2.1.1/)

```bash
pydocstyle --convention=numpy --add-ignore=D401
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
$ mypy -p accounts
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
$ cd <project_root>/docs
$ make html
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
$ sphinx-apidoc -M -f -o docs/source/api/ accounts
```


## TODO

- Add docker image push step to .travis.yml (needs authentication).
- Incorporate JSON schema into documentation.
- Add an example e2e test.
- Add an example controller test.
