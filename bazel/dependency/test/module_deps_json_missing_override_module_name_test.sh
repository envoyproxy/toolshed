#!/bin/bash
set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
  if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
    RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
  else
    RUNFILES_DIR="${TEST_SRCDIR}/_main"
  fi
  FILTER="${RUNFILES_DIR}/dependency/module_deps_json.jq"
  JQ_DIR="${RUNFILES_DIR}/dependency"
  LOCKFILE="${RUNFILES_DIR}/dependency/test/testdata/module/MODULE.bazel.lock"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  FILTER="${SCRIPT_DIR}/../module_deps_json.jq"
  JQ_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
  LOCKFILE="${SCRIPT_DIR}/testdata/module/MODULE.bazel.lock"
fi

declared="$(mktemp)"
err="$(mktemp)"
overridden="$(mktemp)"
trap 'rm -f "${declared}" "${overridden}" "${err}"' EXIT
printf 'aspect_bazel_lib 2.22.0\n' >"${declared}"
printf '(missing)\n' >"${overridden}"
if "${JQ_BIN}" --rawfile declared "${declared}" --rawfile overridden "${overridden}" -L "${JQ_DIR}" -f "${FILTER}" "${LOCKFILE}" >/dev/null 2>"${err}"; then
  echo "expected missing override module_name parse to fail" >&2
  exit 1
fi
grep -F 'Override is missing module_name in MODULE.bazel' "${err}" >/dev/null
