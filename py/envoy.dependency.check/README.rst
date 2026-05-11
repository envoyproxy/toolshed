
envoy.dependency.check
======================

Dependency checker used in Envoy proxy's CI

Prerequisites
-------------

- Python 3.12+
- GitHub access token via ``GITHUB_TOKEN`` or ``--github_token <path>``
- Dependency metadata JSON (for example Envoy ``repository_locations`` output)

Usage
-----

.. code-block:: console

   $ envoy.dependency.check --repository_locations=/path/to/repository_locations.json

Use ``--fix`` to apply safe issue-management fixes (create missing dependency
issues, close stale/duplicate issues, and create missing GitHub labels).

Checks
------

- ``release_dates``: compare recorded dependency release dates with upstream.
- ``release_issues``: validate dependency-upgrade tracking issues and labels.
- ``releases``: detect newer upstream releases or recent post-pin commits.

Input format
------------

The input JSON maps dependency name to
``envoy.dependency.check.typing.DependencyMetadataDict``-compatible metadata.
Each entry must include ``release_date``, ``version``, ``urls``, and
``sha256``.
