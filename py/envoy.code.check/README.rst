
envoy.code.check
================

Code checker used in Envoy proxy's CI.

This package provides an async checker that runs source-code checks against an
Envoy (or Envoy-like) checkout. Registered checks include:

- ``python_flake8`` and ``python_yapf`` for Python style
- ``yamllint`` for YAML files
- ``shellcheck`` for shell scripts
- ``glint`` for file hygiene checks
- ``gofmt`` for Go formatting
- ``runtime_guards`` consistency checks
- extension metadata, registration, owner, and fuzz-coverage checks
- changelog validation, including RST sanity checks

Usage
-----

Installed as a console script:

.. code-block:: console

   $ envoy.code.check --help

Run a subset of checks against a checkout:

.. code-block:: console

   $ envoy.code.check --check python_flake8 python_yapf --path /path/to/envoy

Run only against files changed since a given ref:

.. code-block:: console

   $ envoy.code.check --since main --path /path/to/envoy

See ``envoy.code.check --help`` for the full set of options.

Links
-----

- Source: https://github.com/envoyproxy/toolshed/tree/main/py/envoy.code.check
- Issues: https://github.com/envoyproxy/toolshed/issues
