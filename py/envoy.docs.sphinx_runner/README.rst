
envoy.docs.sphinx_runner
========================

Sphinx docs builder used in Envoy proxy's CI

Overview
--------

``envoy.docs.sphinx_runner`` wraps ``sphinx-build`` to orchestrate the Envoy
proxy documentation build. It implements the ``aio.run.runner.Runner``
lifecycle: validate arguments, check the environment, write a build-config
file, invoke Sphinx, and save the output. Sphinx warnings are treated as
errors (``-W --keep-going``); when the build fails the tail of the captured
warnings file is attached to the exception message to make failures
self-diagnosing. Output is staged to a sibling path first and atomically
swapped into place, so a failed build never destroys an existing output tree
or tarball.

Installation
------------

.. code-block:: bash

    pip install envoy.docs.sphinx_runner

The package registers the console-script entry point
``envoy.docs.sphinx_runner`` (see ``[options.entry_points]`` in
``setup.cfg``).

Usage
-----

.. code-block:: bash

    envoy.docs.sphinx_runner [options] RST_TAR OUTPUT_PATH

Positional arguments
~~~~~~~~~~~~~~~~~~~~

``RST_TAR``
    Path to a tarball containing the RST sources to render. The archive is
    extracted to a temporary build directory before Sphinx is invoked.

``OUTPUT_PATH``
    Destination for the generated docs. When the path looks tar-like
    (``.tar``, ``.tar.gz``, ``.tar.xz``, ``.tar.bz2``), the output is
    packed as a tarball; otherwise it is written as a directory.

Options
~~~~~~~

``--build_sha SHA``
    Git SHA for the build; falls back to ``"UNKNOWN"`` when not supplied.

``--build_target TARGET``
    Sphinx builder name (default: ``html``). Supports any Sphinx builder,
    e.g. ``dirhtml``, ``singlehtml``, ``latex``.

``--docs_tag TAG``
    Explicit docs tag. When omitted, the tag is derived from the
    ``VERSION`` file: non-dev versions produce ``v<version>``; dev versions
    produce an empty tag (pre-release build).

``-j JOBS``, ``--jobs JOBS``
    Sphinx parallel-build job count (default: ``auto``).

``--version_file PATH``
    Path to a ``VERSION`` file containing the semver string.

``--version VERSION``
    Supply the version inline instead of reading ``--version_file``.

``--validator_path PATH``
    Path to a protobuf-validator binary. Presence implies
    ``--validate_fragments``.

``--descriptor_path PATH``
    Path to the protobuf file descriptor used for fragment validation.

``--validate_fragments``
    Enable validation of ``validated-code-block`` RST directives.

``--overwrite``
    Replace an existing ``OUTPUT_PATH``. Without this flag the runner
    raises ``SphinxEnvError`` if the destination already exists.

Example
~~~~~~~

.. code-block:: bash

    envoy.docs.sphinx_runner \
        --build_sha=abcdef1234 \
        --version_file=./VERSION \
        --validator_path=./bin/validator \
        --descriptor_path=./api.pb \
        --validate_fragments \
        --overwrite \
        rst.tar.gz docs.tar.gz

Build configuration (``ENVOY_DOCS_BUILD_CONFIG``)
-------------------------------------------------

Before invoking Sphinx the runner writes a YAML configuration file to a
temporary path and exports that path via the ``ENVOY_DOCS_BUILD_CONFIG``
environment variable. The consumer's ``conf.py`` reads this file to inject
Sphinx settings.

Keys always present:

- ``version_string`` — full version identifier (e.g. ``tag-v1.30.0`` or
  ``1.30.0-abcdef``).
- ``release_level`` — ``"tagged"`` for versioned releases,
  ``"pre-release"`` otherwise.
- ``blob_sha`` — the docs tag when present; otherwise the build SHA.
- ``version_number`` — bare semver string read from the ``VERSION`` file.
- ``docker_image_tag_name`` — Docker image tag derived from the semver
  (e.g. ``v1.29-latest``).
- ``intersphinx_mapping`` — cross-reference mapping built from
  ``versions.yaml`` in the RST tree.

Keys present only when fragment validation is enabled:

- ``validator_path`` — path to the validator binary.
- ``descriptor_path`` — path to the protobuf descriptor.

Key present only when fragment validation is **disabled**:

- ``skip_validation`` — set to ``"true"``; read by the
  ``validated-code-block`` extension to bypass proto checks.

Bundled Sphinx extensions
-------------------------

The package ships three Sphinx extensions under
``envoy/docs/sphinx_runner/ext/``.

``envoy.docs.sphinx_runner.ext.validating_code_block``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Registers the ``validated-code-block`` RST directive, which extends the
standard ``code-block`` directive to validate YAML snippets against a
protobuf type. The required option ``:type-name:`` identifies the full Envoy
API type. Descriptor path and skip-validation settings are read from
``ENVOY_DOCS_BUILD_CONFIG``. An ``ExtensionError`` is raised on validation
failure.

``envoy.docs.sphinx_runner.ext.httpdomain``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wraps ``sphinxcontrib.httpdomain`` with a ``merge_domaindata`` override that
suppresses spurious duplicate-method warnings produced during multi-core
Sphinx builds.

``envoy.docs.sphinx_runner.ext.powershell_lexer``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Registers a PowerShell `Pygments <https://pygments.org/>`_ lexer so that
``.. code-block:: powershell`` blocks are syntax-highlighted correctly.

Enabling the extensions in ``conf.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    extensions = [
        "envoy.docs.sphinx_runner.ext.validating_code_block",
        "envoy.docs.sphinx_runner.ext.httpdomain",
        "envoy.docs.sphinx_runner.ext.powershell_lexer",
        # ... your other extensions
    ]

Error model
-----------

Two exception types are defined in ``envoy.docs.sphinx_runner.exceptions``:

``SphinxEnvError``
    Raised for pre-flight failures: git tag / ``VERSION`` mismatch, missing
    version-history file, or output path exists without ``--overwrite``.

``SphinxBuildError``
    Raised when Sphinx exits with a non-zero code. The message includes the
    exit code and, when available, the tail of the captured warnings file so
    failures are diagnosable without inspecting the full build log.

Development
-----------

Source and issues:
https://github.com/envoyproxy/toolshed/tree/main/py/envoy.docs.sphinx_runner
