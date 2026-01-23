# BoringSSL FIPS Module Registry

This directory contains bzlmod modules for building FIPS-compliant BoringSSL.

## Modules

### `go-fips` (v1.24.12-fips.envoy)

Provides a FIPS-capable Go runtime isolated from Bazel's Minimum Version Selection (MVS). This module is required for building and validating BoringSSL FIPS libraries.

**Why separate from rules_go?**
- Prevents accidental version drift that could compromise FIPS compliance
- Ensures consistent toolchain version across all FIPS builds
- Isolated from MVS dependency resolution

### `boringssl-fips` (fips-20250107.envoy)

Provides FIPS-validated BoringSSL libraries (libcrypto.a and libssl.a) built according to the BoringCrypto security policy.

**Security Guarantees:**
- Build-time validation is MANDATORY and ENFORCED
- Users can NEVER consume unvalidated binaries
- All intermediate build outputs are private
- Only validated libraries are exposed via public targets

## Usage

### In your MODULE.bazel:

```starlark
bazel_dep(name = "boringssl-fips", version = "fips-20250107.envoy")

# The go-fips dependency is automatically pulled in by boringssl-fips
```

### In your BUILD file:

```starlark
load("@rules_cc//cc:defs.bzl", "cc_binary")

cc_binary(
    name = "my_app",
    srcs = ["main.cc"],
    deps = [
        "@boringssl-fips//:crypto",
        "@boringssl-fips//:ssl",
    ],
)
```

## Implementation Details

### Build Process

The FIPS build follows this chain:

1. **Private cmake build** (`_boringssl_build`)
   - Builds BoringSSL with `-DFIPS=1` flag
   - Builds both libraries and the `bssl` validation tool
   - Uses `rules_foreign_cc` cmake() rule
   - Visibility: private (not accessible to consumers)

2. **Private validation** (`_boringssl_validated`)
   - Runs `bssl isfips` to verify FIPS mode (must return "1")
   - Runs FIPS self-tests via `ninja run_tests`
   - Fails the build if validation fails
   - Outputs validated libraries only if tests pass
   - Visibility: private (not accessible to consumers)

3. **Public targets** (`crypto`, `ssl`)
   - Depend on `_boringssl_validated`
   - Can ONLY access validated libraries
   - This is the only way to consume the libraries
   - Visibility: public

### Security Model

**Key Property:** It is impossible to consume unvalidated binaries.

The build enforces this through:
- Private visibility on all unvalidated targets
- Validation as a required dependency of public targets
- Build failure if validation fails
- No escape hatches or bypass mechanisms

### Toolchain Requirements

The modules handle toolchain requirements internally:
- **cmake**: Latest stable (currently 4.2.2) via `rules_foreign_cc`
- **ninja**: Latest stable (currently 1.13.2) via `rules_foreign_cc`
- **Go**: Version 1.24.12 via `go-fips` module
- **LLVM**: Documented as dev_dependency (users should use latest stable)

## Compliance Notes

### FIPS 140-2/140-3

These modules use BoringSSL's `fips-20250107` branch, which targets FIPS 140-2 and 140-3 validation. The validation status depends on:
- Using the exact code version provided
- Following the BoringCrypto module security policy
- Proper integration in your application

**Important:** FIPS compliance is not automatic. You must:
1. Use these modules as-is (no modifications to the build)
2. Ensure your application uses the libraries correctly
3. Follow any additional guidance from NIST/CMVP for your use case

### FedRAMP Guidance

Per FedRAMP requirements:
- Uses latest stable toolchain versions
- Pinned versions prevent drift
- All components are outside MVS

## References

- [BoringSSL FIPS Documentation](https://boringssl.googlesource.com/boringssl/+/refs/heads/main/crypto/fipsmodule/FIPS.md)
- [Go FIPS 140-3 Support](https://go.dev/doc/security/fips140)
- [Envoy FIPS Implementation](https://github.com/envoyproxy/envoy/tree/main/bazel/external)
- [Tracking Issue](https://github.com/envoyproxy/toolshed/issues/3587)

## Platform Support

Currently supported platforms:
- Linux x86_64 (amd64)

**Note:** The current implementation downloads a Linux x86_64 Go binary. For multi-platform support, the modules would need to be extended with platform-specific selections.

## Development

### Based on Envoy's Implementation

These modules are based on Envoy's proven WORKSPACE-based FIPS build, adapted for:
- bzlmod module system instead of WORKSPACE
- `rules_foreign_cc` cmake() instead of raw genrules
- Standalone registry distribution

The validation logic and security model remain identical to Envoy's implementation.

### Testing

To test these modules:
1. Enable bzlmod in your `.bazelrc`: `common --enable_bzlmod`
2. Add the toolshed registry to your MODULE.bazel
3. Build a target that depends on `@boringssl-fips`
4. Verify the validation runs during the build

### Maintenance

When updating:
- **BoringSSL version**: Update to a new `fips-YYYYMMDD` branch
- **Go version**: Update to latest stable with FIPS support
- **Toolchains**: Update cmake/ninja via `rules_foreign_cc` version

Always verify FIPS validation still passes after updates.
