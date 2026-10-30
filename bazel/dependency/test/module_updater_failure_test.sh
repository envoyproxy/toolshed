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

run_update() {
  local stdout="$1"
  local stderr="$2"
  shift 2
  JQ_BIN="${JQ_BIN}" \
  BUILDOZER="${BUILDOZER}" \
  TOOLSHED_JQ_ROOT="${TOOLSHED_JQ_ROOT}" \
  bash "${UPDATE_SCRIPT}" \
    "${tmpdir}/MODULE.bazel" \
    "${tmpdir}/deps.json" \
    --bazelrc="${tmpdir}/report.bazelrc" \
    "$@" >"${stdout}" 2>"${stderr}"
}

assert_module_unchanged() {
  if ! cmp -s "${MODULE_TEMPLATE}" "${tmpdir}/MODULE.bazel"; then
    echo "MODULE.bazel was modified" >&2
    diff "${MODULE_TEMPLATE}" "${tmpdir}/MODULE.bazel" >&2 || true
    exit 1
  fi
}

render_fixture
chmod u+w "${tmpdir}/MODULE.bazel"

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

# --outdated is exclusive with dependency arguments and --report.
set +e
run_update "${stdout}" "${stderr}" --outdated protobuf
rc=$?
set -e
assert_exit_code 1 "${rc}"
grep -F -- '--outdated cannot be combined with dependency arguments' "${stderr}" >/dev/null
assert_module_unchanged

set +e
run_update "${stdout}" "${stderr}" --outdated --report
rc=$?
set -e
assert_exit_code 1 "${rc}"
grep -F -- '--outdated cannot be combined with --report' "${stderr}" >/dev/null

# A bad spec among several leaves MODULE.bazel untouched: the version is checked...
set +e
run_update "${stdout}" "${stderr}" protobuf sq=9.9.9.envoy
rc=$?
set -e
assert_exit_code 1 "${rc}"
grep -F 'Version 9.9.9.envoy for sq is not published' "${stderr}" >/dev/null
assert_module_unchanged

# ...and so is the declaration, before anything is edited.
set +e
run_update "${stdout}" "${stderr}" protobuf aspect_bazel_lib
rc=$?
set -e
assert_exit_code 1 "${rc}"
grep -F 'Dependency aspect_bazel_lib not found' "${stderr}" >/dev/null
assert_module_unchanged

# ...and a dependency may only be requested once.
set +e
run_update "${stdout}" "${stderr}" sq sq=1.4.0.envoy
rc=$?
set -e
assert_exit_code 1 "${rc}"
grep -F 'Dependency sq requested more than once' "${stderr}" >/dev/null
assert_module_unchanged

# A MODULE.bazel that buildozer cannot read fails, rather than every entry being skipped as
# undeclared.
cp "${tmpdir}/MODULE.bazel" "${tmpdir}/MODULE.bazel.orig"
printf 'bazel_dep(name = \n' >> "${tmpdir}/MODULE.bazel"
set +e
run_update "${stdout}" "${stderr}" --outdated
rc=$?
set -e
assert_exit_code 1 "${rc}"
grep -F 'Unable to read bazel_dep declarations' "${stderr}" >/dev/null
mv "${tmpdir}/MODULE.bazel.orig" "${tmpdir}/MODULE.bazel"
assert_module_unchanged

# A failed edit part-way through a batch restores MODULE.bazel.
real_buildozer="${BUILDOZER}"
cat > "${tmpdir}/failing_buildozer" <<FAILING_BUILDOZER
#!/bin/bash
if [[ "\$1" == "set version"* ]]; then
  count=\$(( \$(cat "${tmpdir}/set_count" 2>/dev/null || echo 0) + 1 ))
  echo "\${count}" > "${tmpdir}/set_count"
  if (( count > 1 )); then
    echo "simulated buildozer failure" >&2
    exit 2
  fi
fi
exec "${real_buildozer}" "\$@"
FAILING_BUILDOZER
chmod +x "${tmpdir}/failing_buildozer"
BUILDOZER="${tmpdir}/failing_buildozer"
set +e
run_update "${stdout}" "${stderr}" bazel_skylib protobuf
rc=$?
set -e
BUILDOZER="${real_buildozer}"
assert_exit_code 2 "${rc}"
grep -F 'simulated buildozer failure' "${stderr}" >/dev/null
grep -F 'restored' "${stderr}" >/dev/null
assert_module_unchanged

# Without any bazel_dep, `--outdated` skips every entry as undeclared.
cp "${tmpdir}/MODULE.bazel" "${tmpdir}/MODULE.bazel.orig"
sed -n '/^module(/,/^)/p' "${MODULE_TEMPLATE}" > "${tmpdir}/MODULE.bazel"
run_update "${stdout}" "${stderr}" --outdated
grep -F 'not declared' "${stderr}" >/dev/null
grep -F 'No outdated dependencies declared' "${stdout}" >/dev/null
mv "${tmpdir}/MODULE.bazel.orig" "${tmpdir}/MODULE.bazel"

# Nothing outdated on a registry nobody uses.
run_update "${stdout}" "${stderr}" --outdated=no_such_registry
grep -F 'No outdated dependencies on registries matching no_such_registry' "${stdout}" >/dev/null
assert_module_unchanged
