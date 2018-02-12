Architecture
============

Overview
--------

The arXiv Zero service is a starting-point for developing web services
in the arXiv-NG project. It demonstrates some of the basic patterns for
developing a web service in Flask.

Objectives & Requirements
-------------------------

The arXiv Zero service is responsible for demonstrating the basic internal
architecture for arXiv-NG microservices. It should:

1. Demonstrate the desired project layout for an NG microservice project.
2. Provide an example of a WSGI application implemented in Flask, with the
   desired internal architecture.
3. Demonstrate some patterns for testing parts of the application.
4. Demonstrate how to begin documenting a microservice for NG.
5. Demonstrate the CI/CD and build mechanisms used for NG projects.

Solution Strategy
-----------------
This section shows how you might write the solution strategy section of an
actual NG service.

Context
^^^^^^^

The arXiv Zero service provides a RESTful API that exposes ``baz`` and
``thing`` resources. It is primarily intended for use by API consumers via
the API gateway.

The Zero service relies on the ``Baz`` service to retrieve data about baz'.

Building blocks
^^^^^^^^^^^^^^^

The Zero service is comprised of two main building blocks:

* A Python WSGI application, implemented using Flask.
* The Things data store, a relational database.

Components
^^^^^^^^^^

WSGI
""""
The primary entrypoint for the arXiv Zero service is a Web Server Gateway
Interface application provided by ``wsgi.py`` in the root of the project
(outside of the ``accounts`` package). The WSGI module relies on an application
factory in the :mod:`.factory` module, which is responsible for instantiating
and configuring a Flask application instance upon each HTTP request.

Routes
""""""
The HTTP routes provided by the application are defined in the :mod:`.routes`
module. This module is responsible for routing requests, response
serialization, and authorization.

Each submodule
provides a `blueprint <http://flask.pocoo.org/docs/0.12/blueprints/>`_ object
that describes the HTTP routes available. That blueprint object is attached
to the Flask application upon instantiation.

* :mod:`.routes.external_api`

  - :func:`.routes.external_api.read_baz`
  - :func:`.routes.external_api.read_thing`

Controllers
"""""""""""
Controller modules are the primary point of control for application execution.
These modules orchestrate processing in response to request data, utilizing the
functionality provided by the process and services modules, and generating a
response.

A controller module exposes an internal API for use by the routes modules. The
functions that comprise that API should accept and return native Python data
types. The objects/classes provided by the data domain modules do not escape
beyond this point.

Controller modules may make thoughtful use of Flask utilities and helpers,
taking care not to undermine isolation for unit-testing. The Flask ``request``
proxy object, however, should not be used directly here; interaction with the
client request is the responsibility of the routes modules.

* :mod:`.controllers.baz`
* :mod:`.controllers.things`

Data Domain
"""""""""""
The data domain modules provide descriptions of the data that will be passed
around inside of the application. The objects or classes provided by these
modules provide a shared reference point for the rest of the application. These
descriptions may be as minimal as a set of `type aliases
<https://docs.python.org/3/library/typing.html#type-aliases>`_  built from
native Python data types, or as elaborate as a hierarchy of classes
representing complex data structures. They assist in documentation, testing,
and static analysis.

The objects or classes in this module can be imported and used by the
process, service, and controller modules.

In contrast to some architectures, we don't assume that these structures relate
to anything outside of a given service. They are strictly for reasoning about
data inside of the service. Importantly, these modules **do not** implement
business logic, nor are they concerned with persistence. Those concerns are
left to the process and services modules.

* :mod:`.domain`


Services
""""""""
Service modules provide integrations with external services, including
databases. Each service module is concerned with a single external service, and
provides an API (generally a set of functions) for use by the controller
modules. The functions or methods exposed by each module should accept and
return only native Python types and/or data objects defined in the data domain
module(s).

Modules for integrating with external services and data stores (the Baz service
and the Thing data store) are provided by :mod:`.services`. Each service module
provides a method for preparing the application to use the service (usually a
function called ``init_app()``), and a set of methods for interacting with the
service (e.g. to retrieve or update data). These service modules are used by
the controllers to coordinate interaction with external services on the basis
of client requests.

* :mod:`.services.baz`
* :mod:`.services.things`


Process Modules
"""""""""""""""
Process modules provide data transformation functionality. They encode the
majority of the  business logic of the application. Each process module exposes
an internal API, generally a set of functions representing the use-cases
supported by the module. The functions or methods exposed by each module should
accept and return only native Python types and/or data objects defined in the
data domain modules.

To facilitate testing, process modules should generally be framework-agnostic.
Process modules are imported and used by the controller modules.

* :mod:`.process.mutate`


Static Files & Templates
""""""""""""""""""""""""

.. todo::

   write this section


Cross-cutting Concepts
----------------------

Schema
^^^^^^
Each API endpoint should have a corresponding JSON schema document located in
``schema/``. This will become part of the documentation for this service,
and can also be used for testing.

Deployment
^^^^^^^^^^
The arXiv Zero service is intended to be deployed behind a WSGI application
server in a Docker container.

In this project, we use the `uWSGI
<https://uwsgi-docs.readthedocs.io/en/latest/>`_ application server, which
provides the `uGreen <http://uwsgi-docs.readthedocs.io/en/latest/uGreen.html>`_
thread scheduler for asynchronous request handling.

The ``Dockerfile`` in the root of the project defines the application server
runtime. You can build it with:

.. code-block:: bash

   cd <project root>
   docker build ./ -t arxiv/accounts

arXiv Zero is run within a private network topology, and is exposed to the
outside world via a level 7 load balancer that handles SSL termination. Thus
the Zero service is not responsible for SSL.

Continuous Integration
^^^^^^^^^^^^^^^^^^^^^^
NG projects are tested by `Travis-CI <https://travis-ci.com>`_ on each commit,
PR, and release. See ``.travis.yml`` in the root of this project for a sample
build configuration. See `this documentation
<https://docs.travis-ci.com/user/customizing-the-build/>`_ for details on
customing Travis builds.
