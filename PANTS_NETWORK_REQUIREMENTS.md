# Pants Build System Network Requirements

## Overview

This document details the network endpoints that the Pants build system needs to access during bootstrap, initialization, and normal operation within the envoyproxy/toolshed repository.

## Summary of Required Domains

For quick reference, here are the domains that need to be added to the firewall allowlist:

```
github.com
objects.githubusercontent.com
raw.githubusercontent.com
pypi.org
files.pythonhosted.org
```

## Detailed Network Requirements

### 1. Pants Binary Downloads

**Domain:** `github.com`  
**CDN Domain:** `objects.githubusercontent.com`  
**Purpose:** Download the Pants launcher binary (scie-pants)  
**Required:** Yes (Critical for bootstrap)  
**Details:**
- Pants uses the `get-pants.sh` script to download the launcher binary from GitHub releases
- URL pattern: `https://github.com/pantsbuild/scie-pants/releases/{version}/scie-pants-{os}-{arch}`
- The script downloads both the binary and its SHA256 checksum (`.sha256` file)
- GitHub serves release assets via their CDN at `objects.githubusercontent.com`

**Configuration:**
- Version can be specified in the `get-pants.sh` script via `--version` flag
- Default is `latest/download` which redirects to the most recent release
- This repository uses Pants version `2.23.0` (from `pants.toml`)

### 2. Pants PEX/Wheel Downloads

**Domain:** `github.com`  
**CDN Domain:** `objects.githubusercontent.com`  
**Purpose:** Download the Pants PEX (Python executable) for the configured version  
**Required:** Yes (Critical for initialization)  
**Details:**
- After the launcher binary is installed, Pants downloads its own PEX file
- URL pattern: `https://github.com/pantsbuild/pants/releases/download/release_{version}/pants.{version}.pex`
- The PEX contains the actual Pants implementation
- Also served via GitHub's release CDN

### 3. Python Interpreter Downloads

**Domain:** `github.com`  
**CDN Domain:** `objects.githubusercontent.com`  
**Purpose:** Download Python interpreters for hermetic Python execution  
**Required:** Yes (if using Pants-managed Python interpreters)  
**Details:**
- Pants downloads hermetic Python interpreters from the python-build-standalone project
- URL pattern: `https://github.com/indygreg/python-build-standalone/releases/download/{date}/{python-version}-{platform}.tar.gz`
- This ensures consistent Python versions across environments
- The repository requires Python `>=3.11.0` (from `pants.toml`)

**Configuration:**
- Can be disabled by using system Python interpreters
- Controlled by `[python-bootstrap]` configuration in `pants.toml`
- This repository does not explicitly disable it, so it uses the default (hermetic interpreters)

### 4. PyPI Package Index

**Domain:** `pypi.org`  
**CDN Domain:** `files.pythonhosted.org`  
**Purpose:** Download Python packages and dependencies  
**Required:** Yes (Critical for Python backend)  
**Details:**
- Pants needs to download Python packages specified in lock files
- API requests go to `pypi.org` for package metadata
- Actual package downloads come from `files.pythonhosted.org` (PyPI's CDN)
- This repository has multiple lock files:
  - `deps/deps.lock` (main dependencies)
  - `deps/flake8/flake8.lock` (linting)
  - `deps/pytest/pytest.lock` (testing)
  - `deps/mypy/mypy.lock` (type checking)
- Plugins like `jinja2` are also downloaded from PyPI

### 5. Pants Plugins (via PyPI)

**Domain:** `pypi.org`  
**CDN Domain:** `files.pythonhosted.org`  
**Purpose:** Download Pants plugins if not using custom backends  
**Required:** Depends on configuration  
**Details:**
- This repository uses custom backends (`toolshed_distribution`, `toolshed_readme`)
- These are local plugins, not downloaded from the internet
- If external Pants plugins were specified, they would be downloaded from PyPI

### 6. GitHub Raw Content (Potential)

**Domain:** `raw.githubusercontent.com`  
**Purpose:** Download remote BUILD files, scripts, or configuration from GitHub  
**Required:** No (Optional, used for remote configuration)  
**Details:**
- Some Pants configurations can reference remote BUILD file prelude or macros
- This repository uses local prelude files (`pants-toolshed/macros.py`)
- Include this domain for future flexibility

## Repository-Specific Configuration Analysis

### Enabled Backends
From `pants.toml`, this repository uses:
- `pants.backend.python` - Core Python support (requires PyPI)
- `pants.backend.python.lint.docformatter` - Documentation formatting (requires PyPI)
- `pants.backend.python.lint.flake8` - Python linting (requires PyPI)
- `pants.backend.python.typecheck.mypy` - Type checking (requires PyPI)
- `toolshed_distribution` - Custom local backend (no network requirements)
- `toolshed_readme` - Custom local backend (no network requirements)

### Python Configuration
- Interpreter constraints: `>=3.11.0`
- Multiple named resolves with lock files
- Anonymous telemetry: **disabled** (no telemetry endpoints needed)

### Notable Exclusions
- **Go backend:** Not enabled (no need for Go module proxy)
- **Docker backend:** Not enabled (no need for container registries)
- **Shell backend:** Not enabled
- **Terraform backend:** Not enabled

## Firewall Allowlist Recommendations

### Minimal Required Allowlist

Add these domains to `COPILOT_AGENT_FIREWALL_ALLOW_LIST_ADDITIONS`:

```bash
# Pants binary and release downloads
github.com
objects.githubusercontent.com

# Python packages
pypi.org
files.pythonhosted.org
```

### Recommended Allowlist (includes optional domains)

```bash
# Pants binary and release downloads
github.com
objects.githubusercontent.com
raw.githubusercontent.com

# Python packages
pypi.org
files.pythonhosted.org
```

## Domain Purpose Summary Table

| Domain | Purpose | Required | Used For |
|--------|---------|----------|----------|
| `github.com` | GitHub API and releases | ✅ Yes | Pants launcher, Pants PEX, Python interpreters |
| `objects.githubusercontent.com` | GitHub CDN for release assets | ✅ Yes | Binary and PEX downloads |
| `raw.githubusercontent.com` | GitHub raw content | ⚠️ Optional | Remote configuration files |
| `pypi.org` | Python package index API | ✅ Yes | Package metadata and discovery |
| `files.pythonhosted.org` | PyPI CDN | ✅ Yes | Python package downloads |

## Network Traffic During Pants Lifecycle

### 1. Initial Bootstrap (via `get-pants.sh`)
- Connects to `github.com` → resolves release URL
- Downloads from `objects.githubusercontent.com` → gets `scie-pants-linux-x86_64` binary
- Downloads from `objects.githubusercontent.com` → gets `.sha256` checksum file

### 2. First Run (Pants Initialization)
- Launcher reads `pants.toml` and identifies version `2.23.0`
- Connects to `github.com` → downloads Pants PEX for version 2.23.0
- Connects to `github.com` → downloads Python 3.11+ interpreter (if not cached)
- Downloads from `objects.githubusercontent.com` → gets PEX and Python tarball

### 3. Dependency Resolution
- Reads lock files (`deps/*.lock`)
- Connects to `pypi.org` → validates package metadata
- Downloads from `files.pythonhosted.org` → downloads all packages in lock files
- Caches downloads in `~/.cache/pants/named_caches`

### 4. Normal Operation
- Uses cached binaries, interpreters, and packages
- Only re-downloads if cache is cleared or versions change
- No network access needed for cached builds

## Troubleshooting Network Issues

### Symptoms of Network Restrictions
1. **Hanging during bootstrap:** Likely blocked access to `github.com` or `objects.githubusercontent.com`
2. **Hanging during initialization:** Likely blocked access to Python interpreter downloads
3. **Hanging during dependency resolution:** Likely blocked access to `pypi.org` or `files.pythonhosted.org`
4. **Timeout errors:** Check firewall logs for blocked connections

### Diagnostic Commands

```bash
# Test Pants launcher download
curl -v https://github.com/pantsbuild/scie-pants/releases/latest/download/scie-pants-linux-x86_64

# Test Pants PEX download
curl -v https://github.com/pantsbuild/pants/releases/download/release_2.23.0/pants.2.23.0.pex

# Test Python interpreter download (example)
curl -v https://github.com/indygreg/python-build-standalone/releases/download/20240107/cpython-3.11.7+20240107-x86_64-unknown-linux-gnu-install_only.tar.gz

# Test PyPI access
curl -v https://pypi.org/pypi/jinja2/json
curl -v https://files.pythonhosted.org/packages/ed/55/39036716d19cab0747a5020fc7e907f362fbf48c984b14e62127f7e68e5d/jinja2-3.1.4-py3-none-any.whl
```

### Environment Variables for Debugging

```bash
# Enable verbose logging
export PANTS_LEVEL=debug

# Show network requests
export PANTS_PANTSD_PAILGUN_TIMEOUT=300

# Disable Pantsd daemon (simpler debugging)
export PANTS_PANTSD=false
```

## Alternative Configurations

### Using System Python
If downloading Python interpreters is problematic, you can use system Python:

```toml
[python-bootstrap]
search_path = ["<PATH>"]
```

Add to `pants.toml` and set `<PATH>` to your system Python binary directory.

### Using a PyPI Mirror
If direct PyPI access is blocked, configure a mirror:

```toml
[python-repos]
indexes = ["https://your-pypi-mirror.com/simple/"]
```

### Using Pants in Offline Mode
For completely offline builds (after initial setup):

```bash
./pants --no-pantsd --concurrent test ::
```

Requires pre-populated cache at `~/.cache/pants/`.

## Security Considerations

1. **HTTPS Only:** All downloads use HTTPS (enforced by Pants and `get-pants.sh`)
2. **Checksum Verification:** Pants launcher verifies SHA256 checksums
3. **Lock Files:** Python dependencies are pinned in lock files
4. **No Telemetry:** Anonymous telemetry is disabled in this repository

## References

- Pants documentation: https://www.pantsbuild.org/
- Pants repository: https://github.com/pantsbuild/pants
- Python Build Standalone: https://github.com/indygreg/python-build-standalone
- PyPI: https://pypi.org/
- This repository's Pants version: 2.23.0
