#!/bin/bash
set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
  if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
    RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
  else
    RUNFILES_DIR="${TEST_SRCDIR}/_main"
  fi
  UPDATE_SCRIPT="${RUNFILES_DIR}/dependency/module-update.sh"
  JQ_FILE="${RUNFILES_DIR}/dependency/version.jq"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  UPDATE_SCRIPT="$(cd "${SCRIPT_DIR}/.." && pwd)/module-update.sh"
  JQ_FILE="${SCRIPT_DIR}/../version.jq"
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

cat > "${tmpdir}/deps.json" <<'EOF_JSON'
{
  "bazel_skylib": {
    "version": "1.8.2"
  }
}
EOF_JSON

cat > "${tmpdir}/MODULE.bazel" <<'EOF_MODULE'
module(name = "live_test", version = "0.1.0")
bazel_dep(name = "bazel_skylib", version = "1.8.2")
EOF_MODULE

JQ_BIN="${JQ_BIN}" MODULE_UPDATER_JQ_DIR="${JQ_FILE}" bash "${UPDATE_SCRIPT}" \
  "${tmpdir}/MODULE.bazel" \
  "${tmpdir}/deps.json" \
  --registry=https://bcr.bazel.build/ \
  --report \
  --json-out="${tmpdir}/report.json"

"${JQ_BIN}" -e '.bazel_skylib.latest != null and .bazel_skylib.latest_any != null and (.bazel_skylib.registries | length) == 1' "${tmpdir}/report.json" >/dev/null
