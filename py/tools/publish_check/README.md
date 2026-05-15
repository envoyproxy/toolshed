`check_wheel_metadata.py` is a post-build verification script for CI.

It runs after `pants package ::` and validates built `dist/*.whl` metadata
against each package's `py/*/setup.cfg` `install_requires`.

This check intentionally runs outside the pants test graph because it operates
on already-built wheel artifacts in `dist/` rather than on source targets.
