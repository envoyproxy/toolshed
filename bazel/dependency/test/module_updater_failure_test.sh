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
  ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
  UPDATE_SCRIPT="${ROOT_DIR}/module-update.sh"
  MODULE_TEMPLATE="${SCRIPT_DIR}/testdata/module/MODULE.template.bazel"
  DEPS_TEMPLATE="${SCRIPT_DIR}/testdata/module/deps.template.json"
  BAZELRC_TEMPLATE="${SCRIPT_DIR}/testdata/module/report.bazelrc.template"
  BCR_MARKER="${SCRIPT_DIR}/testdata/module/registry_bcr/REGISTRY_MARKER"
  ENVOY_MARKER="${SCRIPT_DIR}/testdata/module/registry_envoy/REGISTRY_MARKER"
fi

: "${TOOLSHED_JQ_ROOT:?TOOLSHED_JQ_ROOT must be set}"

prepare_workspace() {
  local workspace="$1"
  local bcr_root
  local envoy_root

  bcr_root="$(dirname "${BCR_MARKER}")"
  envoy_root="$(dirname "${ENVOY_MARKER}")"
  sed -e "s|__REGISTRY_BCR__|${bcr_root}|g" -e "s|__REGISTRY_ENVOY__|${envoy_root}|g" "${DEPS_TEMPLATE}" > "${workspace}/deps.json"
  sed -e "s|__REGISTRY_BCR__|${bcr_root}|g" -e "s|__REGISTRY_ENVOY__|${envoy_root}|g" "${BAZELRC_TEMPLATE}" > "${workspace}/.bazelrc"
  cp "${MODULE_TEMPLATE}" "${workspace}/MODULE.bazel"
  chmod u+w "${workspace}/MODULE.bazel"
}

assert_failure() {
  local expected="$1"
  shift
  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "${tmpdir}"' RETURN

  prepare_workspace "${tmpdir}"
  if BUILD_WORKSPACE_DIRECTORY="${tmpdir}" \
    JQ_BIN="${JQ_BIN}" \
    BUILDOZER="${BUILDOZER}" \
    TOOLSHED_JQ_ROOT="${TOOLSHED_JQ_ROOT}" \
    bash "${UPDATE_SCRIPT}" \
      "${tmpdir}/MODULE.bazel" \
      "${tmpdir}/deps.json" \
      --bazelrc="${tmpdir}/.bazelrc" \
      "$@" >"${tmpdir}/stdout" 2>"${tmpdir}/stderr"; then
    echo "expected failure for: $*" >&2
    exit 1
  fi
  grep -F "${expected}" "${tmpdir}/stderr" >/dev/null
  rm -rf "${tmpdir}"
  trap - RETURN
}

assert_success_stdout() {
  local expected="$1"
  shift
  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "${tmpdir}"' RETURN

  prepare_workspace "${tmpdir}"
  BUILD_WORKSPACE_DIRECTORY="${tmpdir}" \
    JQ_BIN="${JQ_BIN}" \
    BUILDOZER="${BUILDOZER}" \
    TOOLSHED_JQ_ROOT="${TOOLSHED_JQ_ROOT}" \
    bash "${UPDATE_SCRIPT}" \
      "${tmpdir}/MODULE.bazel" \
      "${tmpdir}/deps.json" \
      --bazelrc="${tmpdir}/.bazelrc" \
      "$@" >"${tmpdir}/stdout"
  grep -F "${expected}" "${tmpdir}/stdout" >/dev/null
  rm -rf "${tmpdir}"
  trap - RETURN
}

assert_failure "Dependency unknown not found in report" unknown
assert_failure "Version 99.0.0 for protobuf is not published on any configured registry" protobuf=99.0.0
assert_failure "Version 1.9.1 for bazel_skylib is yanked" bazel_skylib=1.9.1
assert_failure "Unable to determine registry for missing_dep; pass --registry" missing_dep
assert_failure "Dependency aspect_bazel_lib not found in" aspect_bazel_lib
assert_failure "Failed to fetch http://127.0.0.1:65535/modules/aspect_bazel_lib/metadata.json" --report --registry=http://127.0.0.1:65535/
assert_failure "Unknown format: bogus" --report --format=bogus
assert_success_stdout "Outdated dependencies: 3 (dev: 1)" --report --format=markdown
assert_success_stdout "| sq _(dev)_ | 1.4.0.envoy | 1.5.0.envoy |" --report --format=markdown
assert_success_stdout "protobuf: already at 35.1.bcr.envoy" protobuf=35.1.bcr.envoy
