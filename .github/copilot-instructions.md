# GitHub Copilot Instructions for envoyproxy/toolshed

## Repository Overview

This repository contains multi-language tooling and libraries for Envoy proxy's CI and development workflows. It includes:

- **py/** - Python packages, libraries, runners, checkers, and dependencies
- **bazel/** - Bazel build configurations and rules
- **rust/** - Rust tooling and libraries
- **gh-actions/** - GitHub Actions workflows
- **sh/** - Shell scripts and utilities

## Build Systems

This repository uses **two build systems**:

### 1. Pants (Primary for Python Development)

Pants is used for Python package development, testing, and linting.

#### Running Pants Commands

```bash
# Run all tests
./pants test ::

# Run tests for a specific package
./pants test envoy.dependency.check::

# Run tests with coverage
./pants test --open-coverage ::

# Lint the code
./pants lint ::

# Debug tests
./pants test --debug envoy.dependency.check::
```

#### Environment Variables for Pants

When working in environments with SSL-intercepting proxies (e.g., corporate proxies with custom certificates):

```bash
# Set the CA certificates path for Pants
export PANTS_CA_CERTS_PATH=/etc/ssl/certs/ca-certificates.crt

# Then run pants commands
./pants test ::
```

**Why this is needed:** Pants (Rust binary) uses compiled-in CA certificates and ignores the system trust store by default. When a proxy intercepts HTTPS with its own CA (e.g., mkcert), Pants fails with `invalid peer certificate: UnknownIssuer`.

#### Pants Network Requirements

Pants requires access to these domains:
- `github.com` / `objects.githubusercontent.com` - Pants releases, PEX tool, Python interpreters
- `pypi.org` / `files.pythonhosted.org` - Python packages

### 2. Bazel (For Build Configurations and Integration)

Bazel is used primarily for build configurations and testing integration with Envoy.

#### Running Bazel Commands

**IMPORTANT:** Always run Bazel commands from the `/bazel` directory or use the full path:

```bash
# Build all targets
cd bazel && bazel build //...

# Test all targets
cd bazel && bazel test //...

# Clean Bazel cache
cd bazel && bazel clean --expunge
```

**Note:** The repository uses WORKSPACE mode for Bazel (bzlmod is disabled via `.bazelrc`). This means dependencies are defined in WORKSPACE files rather than MODULE.bazel.

## Python Package Structure

### Namespaces

- **aio.*** - Generic async packages (not Envoy-specific)
- **envoy.*** - Envoy-specific packages

### Package Types

- **Runners** - Provide functionality by running through a series of steps, exiting on failure
- **Checkers** - Run a series of checks, collecting errors/warnings/success metrics

### Python Version

- Python 3.12+ is required (interpreter constraints: `>=3.12,<3.13`)
- The codebase is "async-first" making extensive use of Python's `asyncio`

## Coding Standards

### Python

- High level of test coverage with unit tests is expected
- Extensive use of type-hinting and type checking (mypy)
- Follow async-first patterns using `asyncio`
- Use `breakpoint()` for debugging with pdb

### Testing

- All code changes must include tests
- Use pytest for testing
- Coverage reports are generated automatically

## Development Workflow

### Linting and Type Checking

The repository uses:
- **flake8** for linting
- **mypy** for type checking
- **docformatter** for docstring formatting

All linting and type checking tools are configured in `pants.toml`.

### Testing in Envoy Environment

When testing toolshed code in an Envoy environment without publishing to PyPI:

1. Edit Envoy's `tools/dev/requirements.txt`
2. Add dev requirements with file path:
   ```
   -e file:///path/to/toolshed/py/envoy.dependency.check#egg=envoy.dependency.check&cachebust=000
   ```
3. Increment `cachebust` parameter when making changes to expire Bazel's cache

## Common Commands Summary

```bash
# Pants: Test everything
./pants test ::

# Pants: Lint everything
./pants lint ::

# Pants: Run with SSL proxy support
export PANTS_CA_CERTS_PATH=/etc/ssl/certs/ca-certificates.crt
./pants test ::

# Bazel: Build everything (from bazel directory)
cd bazel && bazel build //...

# Bazel: Test everything (from bazel directory)
cd bazel && bazel test //...
```

## Important Notes

- Python packages are located in the `py/` subdirectory
- Packages are published to PyPI and used in Envoy via `rules_python`
- The website Bazel packages are consumed by the envoy-website repo
- Pants ignores the `/bazel/` directory (see `pants_ignore` in `pants.toml`)
