# Pants Firewall Allowlist for GitHub Copilot Workspace

## Quick Reference

This document provides the exact firewall allowlist additions needed to run Pants in a GitHub Copilot workspace environment.

## Required Domains for COPILOT_AGENT_FIREWALL_ALLOW_LIST_ADDITIONS

```
github.com
objects.githubusercontent.com
pypi.org
files.pythonhosted.org
```

## Optional But Recommended

```
raw.githubusercontent.com
```

## Domain Breakdown

### Critical for Bootstrap
- **`github.com`** - Pants binary releases, PEX files, Python interpreters
- **`objects.githubusercontent.com`** - GitHub's CDN for release assets

### Critical for Python Dependencies
- **`pypi.org`** - Python package metadata and index
- **`files.pythonhosted.org`** - PyPI's CDN for package downloads

### Optional
- **`raw.githubusercontent.com`** - Remote configuration files (not currently used)

## What Each Domain Is Used For

| Domain | Pants Bootstrap | Pants PEX | Python Interpreter | PyPI Packages |
|--------|----------------|-----------|-------------------|---------------|
| github.com | ✅ | ✅ | ✅ | ❌ |
| objects.githubusercontent.com | ✅ | ✅ | ✅ | ❌ |
| pypi.org | ❌ | ❌ | ❌ | ✅ |
| files.pythonhosted.org | ❌ | ❌ | ❌ | ✅ |

## Expected Network Traffic Order

1. **Bootstrap Phase** (via `./get-pants.sh` or first `./pants` run)
   - Downloads scie-pants binary from `github.com` → `objects.githubusercontent.com`
   
2. **Initialization Phase** (first Pants command)
   - Downloads Pants 2.23.0 PEX from `github.com` → `objects.githubusercontent.com`
   - Downloads Python 3.11+ interpreter from `github.com` → `objects.githubusercontent.com`
   
3. **Dependency Resolution Phase**
   - Downloads Python packages from `pypi.org` → `files.pythonhosted.org`
   - Installs packages from lock files in `deps/` directory

## Verification

After adding domains to allowlist, verify connectivity:

```bash
# Test GitHub access
curl -I https://github.com/pantsbuild/scie-pants/releases
curl -I https://objects.githubusercontent.com/

# Test PyPI access
curl -I https://pypi.org/simple/
curl -I https://files.pythonhosted.org/
```

## Troubleshooting

**Symptom:** Pants hangs after "Bootstrapping Pants" message  
**Likely Cause:** `github.com` or `objects.githubusercontent.com` blocked  
**Solution:** Add both domains to allowlist

**Symptom:** Pants hangs during "Resolving dependencies"  
**Likely Cause:** `pypi.org` or `files.pythonhosted.org` blocked  
**Solution:** Add both domains to allowlist

**Symptom:** Error downloading Python interpreter  
**Likely Cause:** `github.com` blocked for python-build-standalone releases  
**Solution:** Ensure `github.com` and `objects.githubusercontent.com` are allowed

## Additional Information

For comprehensive documentation including diagnostic commands, alternative configurations, and detailed network traffic analysis, see:
- [PANTS_NETWORK_REQUIREMENTS.md](../PANTS_NETWORK_REQUIREMENTS.md)

## Repository Configuration

- Pants Version: `2.23.0` (from `pants.toml`)
- Python Version: `>=3.11.0`
- Backends: Python, flake8, mypy, docformatter, custom local backends
- Telemetry: Disabled (no external telemetry endpoints)
