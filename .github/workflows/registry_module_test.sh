#!/usr/bin/env bash

# Minimal bazel smoke-test for a bazel-registry module version.
#
# Rather than fabricate a consumer workspace, we drive the check from the
# version's own BCR-style `presubmit.yml` `bcr_test_module`, which ships a real
# test module (via `module_path`) that wires the module under test in with a
# `local_path_override`.  We build/test that module's declared targets against
# the in-repo registry, which forces archive download + patch/overlay
# application — proving the mod actually works when consumed.
#
# Environment variables (required):
#   MODULE          – module name (e.g. "librdkafka")
#   MODULE_VERSION  – versioned directory name (e.g. "2.6.0.envoy")
#   MODULES_ROOT    – path to the registry root relative to GITHUB_WORKSPACE
#                     (e.g. "bazel-registry")
#   GITHUB_WORKSPACE – absolute path to the workspace root (set by GitHub Actions)
#
# Opt-out: place a file named "no-bazel-test" in the version directory to skip
# the bazel step.  Useful for modules with very large sources (e.g. wasmtime, v8)
# where even a bare build would be prohibitively slow on a standard runner.

set -e -o pipefail

REGISTRY_ROOT="${GITHUB_WORKSPACE}/${MODULES_ROOT}"
VERSION_DIR="${REGISTRY_ROOT}/modules/${MODULE}/${MODULE_VERSION}"

# ── Opt-out check ────────────────────────────────────────────────────────────
if [[ -f "${VERSION_DIR}/no-bazel-test" ]]; then
    echo "Skipping bazel test for ${MODULE}@${MODULE_VERSION} (no-bazel-test marker present)" >&2
    exit 0
fi

PRESUBMIT="${VERSION_DIR}/presubmit.yml"
if [[ ! -f "${PRESUBMIT}" ]]; then
    echo "::error::No presubmit.yml for ${MODULE}@${MODULE_VERSION} — cannot run module test" >&2
    exit 1
fi

# ── Resolve the test module directory from presubmit.yml ─────────────────────
# `module_path` is relative to the version dir; "" (or unset) means the version
# dir itself is the test module.
MODULE_PATH=$(yq -r '.bcr_test_module.module_path // ""' "${PRESUBMIT}")
TEST_MODULE_DIR="${VERSION_DIR}"
if [[ -n "${MODULE_PATH}" ]]; then
    TEST_MODULE_DIR="${VERSION_DIR}/${MODULE_PATH}"
fi

if [[ ! -f "${TEST_MODULE_DIR}/MODULE.bazel" ]]; then
    # Overlay-based modules ship the test module under overlay/<module_path>.
    if [[ -f "${VERSION_DIR}/overlay/${MODULE_PATH}/MODULE.bazel" ]]; then
        TEST_MODULE_DIR="${VERSION_DIR}/overlay/${MODULE_PATH}"
    else
        echo "::error::No MODULE.bazel found for test module at ${TEST_MODULE_DIR}" >&2
        exit 1
    fi
fi

echo "Testing ${MODULE}@${MODULE_VERSION} via test module ${TEST_MODULE_DIR}" >&2
echo "Registry: ${REGISTRY_ROOT}" >&2

# ── Point the test module at the in-repo registry ────────────────────────────
# BCR is kept as a secondary registry so transitive deps still resolve.
cat > "${TEST_MODULE_DIR}/.bazelrc" <<EOF
common --registry=file://${REGISTRY_ROOT}
common --registry=https://bcr.bazel.build
EOF

cd "${TEST_MODULE_DIR}"

# Collect build/test flags and targets from the first task in presubmit.yml.
# A single task is sufficient for a "does the mod work" smoke check.
readarray -t BUILD_FLAGS < <(yq -r '.bcr_test_module.tasks | to_entries[0].value.build_flags[]? // empty' "${PRESUBMIT}")
readarray -t BUILD_TARGETS < <(yq -r '.bcr_test_module.tasks | to_entries[0].value.build_targets[]? // empty' "${PRESUBMIT}")

if [[ ${#BUILD_TARGETS[@]} -eq 0 ]]; then
    # No explicit targets — just resolve/fetch everything the test module sees.
    BUILD_TARGETS=("//...")
fi

echo "Running: bazel build ${BUILD_FLAGS[*]} ${BUILD_TARGETS[*]}" >&2
bazel build "${BUILD_FLAGS[@]}" "${BUILD_TARGETS[@]}"

echo "✓ ${MODULE}@${MODULE_VERSION} – patches/overlays applied and module builds" >&2
