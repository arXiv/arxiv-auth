# arXiv Auth

This repo provides applications and libraries to support authentication and
authorization, including login, user sessions, account creation(TBD) and API
token management(TBD).

In this repository there are the following:

1. [``arxiv-auth/``](arxiv-auth/) contains the ``arxiv-auth``
   package which provides core authentication and authorization
   functionality and domain classes. This includes integrations with
   the legacy database for user accounts and sessions.
2. [``accounts/``](accounts/) contains a service that provides the
   web UIs for the login/logout pages, registration (TBD), profile
   management(TBD), etc.
3. [``cloud_auth/``](cloud_auth/) **Not in use** authentication for use as a
   FastAPI dependency that checks legacy cookies, NG JWTs and GCP OAuth2 tokens.
3. [``authenticator/``](authenticator/) **Not in use** contains the
   authenticator service. Handles authentication requests from NGINX
   in a cloud deployment scenario.
4. [``registry/``](registry/) **Not in use** contains the API client
   registry application. This implements OAuth2 workflows, client
   registration, and the root API landing page.

# How to get started
To get started look to the README.md for the directory of the component you are
looking to use.

# TODO

- Password reset in ``arxiv.users.legacy.accounts`` and in the accounts service.
- Support for permanent login token.
- Investigate the state of the accounts user registration and clean up, test and document if useful.
- Investigate the state of the authenticator service and clean up, test and document if useful.
- Investigate the state of the registry service and clean up, test and document if useful.

# Code style

All new code should adhere as closely as possible to
[PEP008](https://www.python.org/dev/peps/pep-0008/).

Use the [Numpy style](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt)
for docstrings.

## Linting

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

## Docstyle
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
