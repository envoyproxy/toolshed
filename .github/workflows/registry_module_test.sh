#!/usr/bin/env bash

# Minimal bazel smoke-test for a bazel-registry module version.
#
# Creates a throwaway consumer workspace, points bazel at the in-repo registry,
# then runs `bazel mod deps` followed by `bazel fetch @<module>//...` to force
# archive download and patch/overlay application — without doing any compilation.
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
# where even a bare fetch would be prohibitively slow on a standard runner.

set -e -o pipefail

REGISTRY_ROOT="${GITHUB_WORKSPACE}/${MODULES_ROOT}"
VERSION_DIR="${REGISTRY_ROOT}/modules/${MODULE}/${MODULE_VERSION}"

# ── Opt-out check ────────────────────────────────────────────────────────────
if [[ -f "${VERSION_DIR}/no-bazel-test" ]]; then
    echo "Skipping bazel test for ${MODULE}@${MODULE_VERSION} (no-bazel-test marker present)" >&2
    exit 0
fi

# ── Determine the canonical module name from its own MODULE.bazel ────────────
MODULE_BAZEL="${VERSION_DIR}/MODULE.bazel"
if [[ ! -f "${MODULE_BAZEL}" ]]; then
    # Fall back to overlay/ (some versions place MODULE.bazel there)
    MODULE_BAZEL="${VERSION_DIR}/overlay/MODULE.bazel"
fi

if [[ -f "${MODULE_BAZEL}" ]]; then
    CANONICAL_NAME=$(grep -oP '(?<=name = ")[^"]+' "${MODULE_BAZEL}" | head -1)
else
    CANONICAL_NAME="${MODULE}"
fi

# The registry stores the module under the full ".envoy" directory name and
# metadata.json lists that exact string as the version — so the bazel_dep
# version must match MODULE_VERSION verbatim (do NOT strip ".envoy").
echo "Testing ${CANONICAL_NAME}@${MODULE_VERSION} from registry ${REGISTRY_ROOT}" >&2

# ── Create a throwaway consumer workspace ────────────────────────────────────
CONSUMER_DIR=$(mktemp -d)
trap 'rm -rf "${CONSUMER_DIR}"' EXIT

# We give the module under test a fixed apparent repo name ("mod_under_test")
# via bazel_dep(..., repo_name = ...) so we can reference it directly with a
# single-@ apparent label, without needing to know the version-mangled
# canonical (@@) repo name that bzlmod generates.
cat > "${CONSUMER_DIR}/MODULE.bazel" <<EOF
module(name = "registry_smoke_test", version = "0.0.0")
bazel_dep(name = "${CANONICAL_NAME}", version = "${MODULE_VERSION}", repo_name = "mod_under_test")
EOF

cat > "${CONSUMER_DIR}/BUILD.bazel" <<'EOF'
# intentionally empty – we only need the module to resolve/fetch
EOF

cat > "${CONSUMER_DIR}/.bazelrc" <<EOF
# Use only the local registry + BCR (for transitive deps).
# BCR is kept so that transitive dependencies declared in the module resolve.
common --registry=file://${REGISTRY_ROOT}
common --registry=https://bcr.bazel.build
# Prevent network access from being needed for anything besides the module.
EOF

# ── Run bazel mod deps (forces lock-file resolution + fetch) ─────────────────
echo "Running: bazel mod deps" >&2
cd "${CONSUMER_DIR}"
bazel mod deps

# `bazel mod deps` resolves the module graph but does not necessarily fetch the
# repository (which is what applies patches/overlays). Force the fetch via the
# apparent repo name we assigned above so we don't depend on the mangled
# canonical (@@) name.
echo "Running: bazel fetch @mod_under_test//..." >&2
bazel fetch "@mod_under_test//..."

echo "✓ ${CANONICAL_NAME}@${MODULE_VERSION} – patches/overlays applied successfully" >&2
