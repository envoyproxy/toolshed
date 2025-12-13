# Python Packages

This directory contains all Python packages for the Envoy toolshed project.

## Core Packages

### Generic Packages (aio.* namespace)

These packages provide Python `async` functionality and are not specific to Envoy:

- [abstracts](abstracts) - Abstract base classes and interfaces
- [aio.api.bazel](aio.api.bazel) - Async API for Bazel
- [aio.api.github](aio.api.github) - Async API for GitHub
- [aio.api.nist](aio.api.nist) - Async API for NIST
- [aio.core](aio.core) - Core async utilities
- [aio.run.checker](aio.run.checker) - Async checker runner
- [aio.run.runner](aio.run.runner) - Async task runner

### Envoy-specific Packages (envoy.* namespace)

These packages are specific to Envoy or work to Envoy's specific requirements:

- [envoy.base.utils](envoy.base.utils) - Base utilities for Envoy
- [envoy.ci.report](envoy.ci.report) - CI reporting tools
- [envoy.code.check](envoy.code.check) - Code checking and linting
- [envoy.dependency.check](envoy.dependency.check) - Dependency integrity checking
- [envoy.distribution.distrotest](envoy.distribution.distrotest) - Distribution testing
- [envoy.distribution.release](envoy.distribution.release) - Release management
- [envoy.distribution.repo](envoy.distribution.repo) - Repository management
- [envoy.distribution.verify](envoy.distribution.verify) - Distribution verification
- [envoy.docker.utils](envoy.docker.utils) - Docker utilities
- [envoy.docs.sphinx_runner](envoy.docs.sphinx_runner) - Sphinx documentation runner
- [envoy.github.abstract](envoy.github.abstract) - GitHub abstractions
- [envoy.github.release](envoy.github.release) - GitHub release management
- [envoy.gpg.identity](envoy.gpg.identity) - GPG identity management
- [envoy.gpg.sign](envoy.gpg.sign) - GPG signing utilities

### Other Packages

- [dependatool](dependatool) - Dependency management tool
- [mypy-abstracts](mypy-abstracts) - MyPy plugin for abstracts
- [pytest-abstracts](pytest-abstracts) - Pytest plugin for abstracts
- [pytest-iters](pytest-iters) - Pytest plugin for iterators
- [pytest-patches](pytest-patches) - Pytest plugin for patches

## Build System

- [pants-toolshed](pants-toolshed) - Pants build system macros and plugins
- [deps](deps) - Python dependency lock files and requirements

## PyPI Publication

All packages are published to [PyPI](https://pypi.org/) with their original names. When published packages reference their source locations, they continue to use the package name (e.g., `abstracts`, `aio.core`, etc.) as the project home, maintaining compatibility with existing installations.

## Development

See the main [DEVELOPER.md](../DEVELOPER.md) for information on testing and linting with pants.
