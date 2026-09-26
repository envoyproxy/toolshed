#!/bin/bash

set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
    if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
        RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
    else
        RUNFILES_DIR="${TEST_SRCDIR}/_main"
    fi
    RESOLVE_SCRIPT="${RUNFILES_DIR}/dependency/registry-resolve.sh"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    RUNFILES_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
    RESOLVE_SCRIPT="${RUNFILES_DIR}/registry-resolve.sh"
fi

: "${GIT_BIN:?GIT_BIN must be set}"
: "${JQ_BIN:?JQ_BIN must be set}"
: "${TOOLSHED_JQ_ROOT:?TOOLSHED_JQ_ROOT must be set}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

WORK_REPO="${tmpdir}/work"
BARE_REPO="${tmpdir}/registry.git"
REPO_URL="file://${BARE_REPO}"
BASE_URL="https://raw.githubusercontent.com/envoyproxy/bazel-registry"

"${GIT_BIN}" init --bare "${BARE_REPO}" >/dev/null
"${GIT_BIN}" init -b main "${WORK_REPO}" >/dev/null
"${GIT_BIN}" -C "${WORK_REPO}" config user.name 'Test User'
"${GIT_BIN}" -C "${WORK_REPO}" config user.email 'test@example.com'

printf 'one
' > "${WORK_REPO}/registry.txt"
"${GIT_BIN}" -C "${WORK_REPO}" add registry.txt
"${GIT_BIN}" -C "${WORK_REPO}" commit -m 'first' >/dev/null

printf 'two
' > "${WORK_REPO}/registry.txt"
"${GIT_BIN}" -C "${WORK_REPO}" commit -am 'second' >/dev/null
SECOND_SHA="$("${GIT_BIN}" -C "${WORK_REPO}" rev-parse HEAD)"
"${GIT_BIN}" -C "${WORK_REPO}" tag v0.1.0 "${SECOND_SHA}"

printf 'three
' > "${WORK_REPO}/registry.txt"
"${GIT_BIN}" -C "${WORK_REPO}" commit -am 'third' >/dev/null
LATEST_SHA="$("${GIT_BIN}" -C "${WORK_REPO}" rev-parse HEAD)"

"${GIT_BIN}" -C "${WORK_REPO}" checkout --orphan stray >/dev/null
rm -f "${WORK_REPO}/registry.txt"
printf 'stray
' > "${WORK_REPO}/stray.txt"
"${GIT_BIN}" -C "${WORK_REPO}" add stray.txt
"${GIT_BIN}" -C "${WORK_REPO}" commit -m 'stray' >/dev/null
STRAY_SHA="$("${GIT_BIN}" -C "${WORK_REPO}" rev-parse HEAD)"

"${GIT_BIN}" -C "${WORK_REPO}" push "${REPO_URL}" main stray --tags >/dev/null
"${GIT_BIN}" -C "${WORK_REPO}" checkout main >/dev/null

run_resolve() {
    local stdout="$1"
    local stderr="$2"
    shift 2
    bash "${RESOLVE_SCRIPT}" resolve         --repo="${REPO_URL}"         --url="${BASE_URL}"         --branch=main         --git-bin="${GIT_BIN}"         --jq-bin="${JQ_BIN}"         --jq-root="${TOOLSHED_JQ_ROOT}"         "$@" >"${stdout}" 2>"${stderr}"
}

run_check() {
    local bazelrc="$1"
    local stdout="$2"
    local stderr="$3"
    shift 3
    bash "${RESOLVE_SCRIPT}" check         --repo="${REPO_URL}"         --url="${BASE_URL}"         --branch=main         --bazelrc="${bazelrc}"         --git-bin="${GIT_BIN}"         --jq-bin="${JQ_BIN}"         --jq-root="${TOOLSHED_JQ_ROOT}"         "$@" >"${stdout}" 2>"${stderr}"
}

write_bazelrc() {
    local path="$1"
    local sha="$2"
    cat > "${path}" <<EOF_BAZELRC
common --registry=https://bcr.bazel.build/
common --registry=${BASE_URL}/${sha}
common:ci --registry=${BASE_URL}/${sha}
EOF_BAZELRC
}

assert_exit_code() {
    local expected="$1"
    local actual="$2"
    if [[ "${expected}" != "${actual}" ]]; then
        echo "expected exit code ${expected}, got ${actual}" >&2
        exit 1
    fi
}

stdout="${tmpdir}/stdout"
stderr="${tmpdir}/stderr"

run_resolve "${stdout}" "${stderr}"
"${JQ_BIN}" -e --arg latest "${LATEST_SHA}" '.sha == $latest and .latest == $latest and .ancestor == true and .tags == [] and .requested == "" and .unsafe == false' "${stdout}" >/dev/null

run_resolve "${stdout}" "${stderr}" --requested-sha="${SECOND_SHA}"
"${JQ_BIN}" -e --arg sha "${SECOND_SHA}" '.sha == $sha and .tags == ["v0.1.0"] and .ancestor == true and .unsafe == false' "${stdout}" >/dev/null

set +e
run_resolve "${stdout}" "${stderr}" --requested-sha="${STRAY_SHA}"
rc=$?
set -e
assert_exit_code 2 "${rc}"
grep -F 'not an ancestor' "${stderr}" >/dev/null

run_resolve "${stdout}" "${stderr}" --requested-sha="${STRAY_SHA}" --allow-unsafe
"${JQ_BIN}" -e '.ancestor == false and .unsafe == true' "${stdout}" >/dev/null
grep -F 'WARNING:' "${stderr}" >/dev/null

set +e
run_resolve "${stdout}" "${stderr}" --requested-sha=deadbeef
rc=$?
set -e
assert_exit_code 2 "${rc}"

run_resolve "${stdout}" "${stderr}" --release-tags='v*'
"${JQ_BIN}" -e --arg sha "${SECOND_SHA}" '.sha == $sha and .latest != $sha and .tags == ["v0.1.0"]' "${stdout}" >/dev/null

pinned_bazelrc="${tmpdir}/pinned.bazelrc"
write_bazelrc "${pinned_bazelrc}" "${SECOND_SHA}"
run_check "${pinned_bazelrc}" "${stdout}" "${stderr}"
"${JQ_BIN}" -e --arg sha "${SECOND_SHA}" '.sha == $sha and .ancestor == true and .behind == 1 and .tags == ["v0.1.0"]' "${stdout}" >/dev/null

stray_bazelrc="${tmpdir}/stray.bazelrc"
write_bazelrc "${stray_bazelrc}" "${STRAY_SHA}"
set +e
run_check "${stray_bazelrc}" "${stdout}" "${stderr}"
rc=$?
set -e
assert_exit_code 2 "${rc}"
