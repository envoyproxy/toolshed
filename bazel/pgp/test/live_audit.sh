#!/usr/bin/env bash
#
# Captures the real dependency graph of the example signing targets in this
# package, then audits the capture with `//pgp/audit:audit`.
#
# This is the live counterpart to `//pgp/test:audit_test`: it actually
# re-invokes `bazel aquery` so a regression that only shows up in the real
# graph (eg a dropped execution requirement, or a leaked `HOME`) is caught in
# CI. The audit itself still runs through `//pgp/audit:audit`, whose launcher
# invokes jq from runfiles, not from PATH.
#
# Intended to be run with `bazel run //pgp/test:live_audit` from the
# workspace root - it shells out to a fresh `bazel aquery` invocation, so it
# cannot run as a sandboxed `bazel test`.

set -euo pipefail

workspace="${BUILD_WORKSPACE_DIRECTORY:?must be run with \`bazel run\`}"
cd "$workspace"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

pattern="deps(//pgp/test:example_detached) + deps(//pgp/test:example_cleartext) + deps(//pgp/test:example_checksums) + deps(//pgp/test:example_deb_changes)"

bazel aquery --output=jsonproto --include_artifacts=true \
    --@envoy_toolshed//pgp:key_path=/tmp/nonexistent-key#sha256=0000000000000000000000000000000000000000000000000000000000000000 \
    --@envoy_toolshed//pgp:passphrase_path=/tmp/nonexistent \
    "$pattern" > "$tmp/aquery.json"

bazel build //pgp/audit:audit
bazel_bin="$(bazel info bazel-bin)"
RUNFILES_DIR="$bazel_bin/pgp/audit/audit.sh.runfiles" \
    "$bazel_bin/pgp/audit/audit.sh" --aquery-json "$tmp/aquery.json"
