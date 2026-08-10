# bazel-registry

This directory contains a private Bazel module registry for Envoy-patched
versions of upstream libraries.  Module versions are named `<version>.envoy`
and can include `patches/` and/or an `overlay/` (BCR-style).

## CI validation

Two checks run for every `*.envoy` version in CI:

### 1. Integrity / hash check

[`.github/workflows/registry_integrity.sh`](../.github/workflows/registry_integrity.sh)
downloads the upstream archive and recomputes the `sha256` of the archive and
every file under `overlay/` and `patches/`, then compares them against the
values recorded in `source.json`.  This ensures the patch and overlay *files
themselves* are unmodified.

### 2. Bazel module smoke test (patch-apply check)

[`.github/workflows/registry_module_test.sh`](../.github/workflows/registry_module_test.sh)
creates a throwaway consumer workspace with a single `bazel_dep(...)` pointing
at this registry and runs:

```
bazel mod deps
bazel fetch @@<module>//...
```

This forces Bazel to download the upstream archive and apply all patches and
overlays exactly as a real consumer would.  The job fails if any patch does not
apply cleanly, giving early warning of upstream drift or malformed offsets before
the module is actually used in Envoy.

BCR is kept as a secondary registry so that transitive dependencies declared in
the module's `MODULE.bazel` continue to resolve; only the *primary* module under
test is served from the local registry.

### Opting a module version out of the smoke test

For modules with very large upstream archives (e.g. wasmtime, v8) even a bare
`bazel fetch` can be prohibitively slow or require infrastructure not present on
a standard GitHub Actions runner.  To skip the bazel smoke test for a specific
version, create an empty (or single-line) file named `no-bazel-test` in the
version directory:

```
bazel-registry/modules/<module>/<version>.envoy/no-bazel-test
```

The file content is ignored; its presence is the signal.  Document the reason
inside the file.  The integrity/hash check still runs for opted-out versions.

**Current opt-outs:**

| Module    | Version      | Reason                                        |
|-----------|--------------|-----------------------------------------------|
| wasmtime  | 24.0.0.envoy | Upstream archive is very large (~GB); fetch would time out on a standard runner |
| wasmtime  | 45.0.2.envoy | Same reason as above                          |
