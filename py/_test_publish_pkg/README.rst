_test_publish_pkg
=================

Toolshed test fixture for publish metadata validation.

This package exists solely as a test fixture to exercise the publish
pipeline and verify that built wheel METADATA contains loose ranges
from setup.cfg rather than pinned ``==`` versions from the dev resolve.

Do not publish this package to PyPI.
