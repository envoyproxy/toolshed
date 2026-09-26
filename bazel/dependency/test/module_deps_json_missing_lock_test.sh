#!/bin/bash
set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
  if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
    RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
  else
    RUNFILES_DIR="${TEST_SRCDIR}/_main"
  fi
  DECLARED="${RUNFILES_DIR}/dependency/test/testdata/module/module_deps_missing_lock.declared.txt"
  FILTER="${RUNFILES_DIR}/dependency/module_deps_json.jq"
  JQ_DIR="${RUNFILES_DIR}/dependency"
  LOCKFILE="${RUNFILES_DIR}/dependency/test/testdata/module/MODULE.bazel.lock"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  DECLARED="${SCRIPT_DIR}/testdata/module/module_deps_missing_lock.declared.txt"
  FILTER="${SCRIPT_DIR}/../module_deps_json.jq"
  JQ_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
  LOCKFILE="${SCRIPT_DIR}/testdata/module/MODULE.bazel.lock"
fi

err="$(mktemp)"
overridden="$(mktemp)"
trap 'rm -f "${overridden}" "${err}"' EXIT
: >"${overridden}"
if "${JQ_BIN}" --rawfile declared "${DECLARED}" --rawfile overridden "${overridden}" -L "${JQ_DIR}" -f "${FILTER}" "${LOCKFILE}" >/dev/null 2>"${err}"; then
  echo "expected missing lockfile dependency parse to fail" >&2
  exit 1
fi
grep -F 'Declared dependency sq not found in MODULE.bazel.lock; regenerate the lockfile' "${err}" >/dev/null
