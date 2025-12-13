# Pants SSL Certificate Issue - Root Cause and Solution

## TL;DR - The Real Problem

**The issue is NOT that domains are blocked.** The firewall/proxy is performing **SSL/TLS interception** (MITM), and Pants doesn't trust the proxy's CA certificate.

## What We Discovered

### 1. Initial Symptoms
- Pants appears to "hang" during initialization
- No error messages visible without debug logging
- Downloads seem to never complete

### 2. Root Cause (Found via Debug Logging)
```bash
~/.local/bin/pants --level=debug --no-pantsd --version
```

**Error:**
```
Error while downloading https://github.com/pex-tool/pex/releases/download/v2.16.2/pex: 
Error downloading file: error sending request for url: 
error trying to connect: invalid peer certificate: UnknownIssuer (retryable)
```

### 3. Certificate Investigation
```bash
$ openssl s_client -connect github.com:443 -servername github.com < /dev/null 2>/dev/null | openssl x509 -noout -issuer -subject
```

**Result:**
```
issuer=O = mkcert development CA, OU = runner@runnervm6qbrg, CN = mkcert runner@runnervm6qbrg
subject=O = GoProxy untrusted MITM proxy Inc, CN = github.com
```

**Key Finding:** The certificate is signed by `mkcert development CA`, not by a legitimate CA like DigiCert or Let's Encrypt.

## Why Adding the CA to System Trust Store Didn't Work

We added the mkcert CA certificate to `/usr/local/share/ca-certificates/` and ran `update-ca-certificates`, but Pants still failed with the same error.

### Root Cause
**Pants is a Rust binary** that uses the `reqwest` HTTP client library. In some environments or builds, Rust's reqwest may:

1. Use a **statically linked certificate bundle** (embedded in the binary)
2. Not read from the system's CA certificate store
3. Only trust its built-in set of CAs

This is a known issue with Rust applications in environments using custom CAs or SSL interception proxies.

## The Solution: Options Available

### Option 1: Bypass SSL Interception (RECOMMENDED)

**What:** Configure the firewall/proxy to NOT intercept HTTPS traffic for specific domains.

**How:** In the firewall configuration, add these domains to an SSL bypass list:
- `github.com`
- `*.github.com` (or specifically `objects.githubusercontent.com`)
- `pypi.org`
- `files.pythonhosted.org`

**Why this works:** Traffic flows directly from Pants to the destination with legitimate certificates.

**Pros:**
- ✅ No modification to Pants or the environment needed
- ✅ Pants sees legitimate certificates it already trusts
- ✅ Most secure and reliable solution

**Cons:**
- ⚠️ Requires firewall/proxy administrator access
- ⚠️ Reduces visibility into encrypted traffic for these domains

### Option 2: Use Pants with Environment Variable (May Not Work)

**What:** Try setting environment variables that some Rust applications respect.

**Commands to try:**
```bash
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export SSL_CERT_DIR=/etc/ssl/certs
export CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

~/.local/bin/pants --version
```

**Status:** These variables are already set in the Copilot Workspace environment, but Pants still fails, indicating **this does not work** for the Pants binary.

### Option 3: Rebuild Pants with System CA Support (NOT RECOMMENDED)

**What:** Compile Pants from source with webpki-roots disabled and native-certs enabled.

**Why NOT recommended:**
- ❌ Very complex and time-consuming
- ❌ Requires Rust toolchain
- ❌ Need to maintain custom builds
- ❌ May break with Pants updates

### Option 4: Use a Pre-Downloaded Cache (Workaround)

**What:** Manually download all required files and populate Pants cache, then run offline.

**Steps:**
1. Download on a machine without SSL interception:
   - `https://github.com/pex-tool/pex/releases/download/v2.16.2/pex`
   - All Python packages from PyPI (lock files)
   - Python interpreters if needed

2. Copy to `~/.cache/pants/` in the appropriate structure

3. Run Pants in offline/cached mode

**Pros:**
- ✅ Works around the SSL issue
- ✅ No firewall changes needed

**Cons:**
- ⚠️ Manual process, hard to maintain
- ⚠️ Cache needs updating when dependencies change
- ⚠️ Not practical for CI/CD

## Recommended Action

**Contact the GitHub Copilot Workspace / Firewall Administrator** and request:

> "Please configure the firewall to bypass SSL interception for the following domains:
> - github.com
> - objects.githubusercontent.com  
> - pypi.org
> - files.pythonhosted.org
>
> These domains are required for the Pants build system, which uses a Rust HTTP client that cannot work with SSL interception proxies."

## Technical Details

### Why Rust Applications Have This Problem

Rust's `reqwest` library (used by Pants) has two certificate verification backends:

1. **webpki** (default): Uses a statically-compiled list of trusted CAs
   - Embedded in the binary at compile time
   - Does NOT read system CA certificates
   - Cannot be updated without recompiling

2. **native-tls**: Uses the operating system's certificate store
   - Reads from `/etc/ssl/certs/` on Linux
   - Can be configured at runtime
   - **Not enabled in the pre-built Pants binaries**

### Verification

You can verify SSL interception is happening:
```bash
# Check what certificate is presented
openssl s_client -connect github.com:443 -servername github.com < /dev/null 2>&1 | grep -E "issuer|subject"

# If you see "mkcert" or "GoProxy" or your corporate proxy name, SSL interception is active
```

You can verify the CA certificate is in the system store:
```bash
# Check if mkcert CA is trusted by curl (it should be after we added it)
curl -v https://github.com 2>&1 | grep "SSL certificate verify"
# Should show: "SSL certificate verify ok."

# But Pants still fails:
~/.local/bin/pants --level=debug --version 2>&1 | grep "certificate"
# Shows: "invalid peer certificate: UnknownIssuer"
```

## URLs That Pants Needs (For Firewall Bypass Configuration)

### Critical - Must bypass SSL interception
1. `github.com` - For Pants releases, PEX tool, Python interpreters
2. `objects.githubusercontent.com` - GitHub CDN for release assets
3. `pypi.org` - Python package index
4. `files.pythonhosted.org` - PyPI CDN

### Optional - May improve reliability
5. `raw.githubusercontent.com` - For remote configuration (rarely used)

## Summary

1. **Problem:** SSL interception proxy breaks Pants' certificate validation
2. **Why:** Pants (Rust binary) uses compiled-in CA list, ignores system trust store
3. **Solution:** Configure firewall to bypass SSL interception for GitHub and PyPI domains
4. **Alternative:** None that work reliably without firewall changes

## Files in This Repository

- `PANTS_NETWORK_REQUIREMENTS.md` - Comprehensive network requirements documentation
- `.github/PANTS_FIREWALL_ALLOWLIST.md` - Quick reference for domains
- `.github/PANTS_SSL_FIX.md` - This file, explaining the SSL issue
- `.github/scripts/test-pants-network.sh` - Script to test network connectivity
