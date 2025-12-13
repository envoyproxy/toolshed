# SOLUTION: Running Pants with SSL Interception Proxy

## The Problem

Pants hangs when trying to download files because the firewall/proxy performs SSL interception (MITM), and Pants doesn't trust the proxy's CA certificate by default.

## The Solution

Set the `PANTS_CA_CERTS_PATH` environment variable to point to the system CA bundle:

```bash
export PANTS_CA_CERTS_PATH=/etc/ssl/certs/ca-certificates.crt
```

Then run pants normally:

```bash
pants test ::
pants lint ::
pants --version
```

## How to Make This Permanent

### Option 1: Add to your shell profile

Add to `~/.bashrc` or `~/.zshrc`:
```bash
export PANTS_CA_CERTS_PATH=/etc/ssl/certs/ca-certificates.crt
```

### Option 2: Set in pants.toml (project-wide)

Add to `pants.toml`:
```toml
[GLOBAL]
ca_certs_path = "/etc/ssl/certs/ca-certificates.crt"
```

### Option 3: Set via environment file

Create `.env` file in your project:
```
PANTS_CA_CERTS_PATH=/etc/ssl/certs/ca-certificates.crt
```

And source it before running pants:
```bash
source .env
pants test ::
```

## Verification

Test that it works:

```bash
# Set the environment variable
export PANTS_CA_CERTS_PATH=/etc/ssl/certs/ca-certificates.crt

# Run pants
cd /path/to/toolshed
pants --version
# Should output: 2.23.0

# Run tests
pants test ::
# Should run all tests
```

## Why This Works

1. **The Proxy Issue**: The firewall/proxy intercepts HTTPS connections and presents its own certificate (signed by `mkcert development CA`)
2. **Pants Default Behavior**: Pants (being a Rust binary) uses a compiled-in list of trusted CAs and doesn't read the system CA store by default
3. **The Fix**: `PANTS_CA_CERTS_PATH` tells Pants to use the system CA bundle, which includes the mkcert CA certificate (added via `update-ca-certificates`)

## What Network Domains Pants Needs

Even with the SSL fix, ensure these domains are accessible (not blocked):

1. **github.com** - Pants releases, PEX tool, Python interpreters
2. **objects.githubusercontent.com** - GitHub CDN for release assets  
3. **pypi.org** - Python package index
4. **files.pythonhosted.org** - PyPI CDN for packages

## Tested and Working

Successfully ran:
```bash
PANTS_CA_CERTS_PATH=/etc/ssl/certs/ca-certificates.crt pants test ::
```

Result: 354 tests passed, 4 failed (unrelated to network issues - actual test failures in the codebase)

## For CI/CD

In GitHub Actions or other CI systems, add:

```yaml
env:
  PANTS_CA_CERTS_PATH: /etc/ssl/certs/ca-certificates.crt
```

Or in your workflow:
```yaml
- name: Run Pants tests
  run: pants test ::
  env:
    PANTS_CA_CERTS_PATH: /etc/ssl/certs/ca-certificates.crt
```
