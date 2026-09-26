#!/bin/bash
set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
  if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
    RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
  else
    RUNFILES_DIR="${TEST_SRCDIR}/_main"
  fi
  UPDATE_SCRIPT="${RUNFILES_DIR}/dependency/module-update.sh"
  MODULE_TEMPLATE="${RUNFILES_DIR}/dependency/test/testdata/module/MODULE.template.bazel"
  DEPS_TEMPLATE="${RUNFILES_DIR}/dependency/test/testdata/module/deps.template.json"
  BAZELRC_TEMPLATE="${RUNFILES_DIR}/dependency/test/testdata/module/report.bazelrc.template"
  BCR_MARKER="${RUNFILES_DIR}/dependency/test/testdata/module/registry_bcr/REGISTRY_MARKER"
  ENVOY_MARKER="${RUNFILES_DIR}/dependency/test/testdata/module/registry_envoy/REGISTRY_MARKER"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  RUNFILES_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
  UPDATE_SCRIPT="${RUNFILES_DIR}/module-update.sh"
  MODULE_TEMPLATE="${RUNFILES_DIR}/test/testdata/module/MODULE.template.bazel"
  DEPS_TEMPLATE="${RUNFILES_DIR}/test/testdata/module/deps.template.json"
  BAZELRC_TEMPLATE="${RUNFILES_DIR}/test/testdata/module/report.bazelrc.template"
  BCR_MARKER="${RUNFILES_DIR}/test/testdata/module/registry_bcr/REGISTRY_MARKER"
  ENVOY_MARKER="${RUNFILES_DIR}/test/testdata/module/registry_envoy/REGISTRY_MARKER"
fi

: "${TOOLSHED_JQ_ROOT:?TOOLSHED_JQ_ROOT must be set}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

assert_exit_code() {
  local expected="$1"
  local actual="$2"
  if [[ "${expected}" != "${actual}" ]]; then
    echo "expected exit code ${expected}, got ${actual}" >&2
    exit 1
  fi
}

render_fixture() {
  local bcr_root
  local envoy_root

  bcr_root="$(dirname "${BCR_MARKER}")"
  envoy_root="$(dirname "${ENVOY_MARKER}")"
  cp "${MODULE_TEMPLATE}" "${tmpdir}/MODULE.bazel"
  sed -e "s|__REGISTRY_BCR__|${bcr_root}|g" -e "s|__REGISTRY_ENVOY__|${envoy_root}|g" "${DEPS_TEMPLATE}" > "${tmpdir}/deps.json"
  sed -e "s|__REGISTRY_BCR__|${bcr_root}|g" -e "s|__REGISTRY_ENVOY__|${envoy_root}|g" "${BAZELRC_TEMPLATE}" > "${tmpdir}/report.bazelrc"
}

run_report() {
  local stdout="$1"
  local stderr="$2"
  shift 2
  JQ_BIN="${JQ_BIN}" \
  TOOLSHED_JQ_ROOT="${TOOLSHED_JQ_ROOT}" \
  bash "${UPDATE_SCRIPT}" \
    "${tmpdir}/MODULE.bazel" \
    "${tmpdir}/deps.json" \
    --bazelrc="${tmpdir}/report.bazelrc" \
    --report \
    "$@" >"${stdout}" 2>"${stderr}"
}

render_fixture

stdout="${tmpdir}/stdout"
stderr="${tmpdir}/stderr"
report_json="${tmpdir}/report.json"

JQ_BIN="${JQ_BIN}" \
TOOLSHED_JQ_ROOT="${TOOLSHED_JQ_ROOT}" \
bash "${UPDATE_SCRIPT}" \
  "${tmpdir}/MODULE.bazel" \
  "${tmpdir}/deps.json" \
  --bazelrc="${tmpdir}/report.bazelrc" \
  --report \
  --json-out="${report_json}"

"${JQ_BIN}" -e '.bazel_skylib.latest != null and .bazel_skylib.latest_any != null and (.bazel_skylib.registries | length) == 1' "${report_json}" >/dev/null

set +e
run_report "${stdout}" "${stderr}" --format=bogus
rc=$?
set -e
assert_exit_code 1 "${rc}"
grep -F 'Unknown format' "${stderr}" >/dev/null

run_report "${stdout}" "${stderr}" --format=markdown
test "$(head -n 1 "${stdout}")" = 'Outdated dependencies: 3 (dev: 1)'
grep -F '| sq _(dev)_ |' "${stdout}" >/dev/null

set +e
run_report "${stdout}" "${stderr}" --fail-on-outdated-dev
rc=$?
set -e
assert_exit_code 1 "${rc}"

set +e
run_report "${stdout}" "${stderr}" --fail-on-outdated
rc=$?
set -e
assert_exit_code 1 "${rc}"
