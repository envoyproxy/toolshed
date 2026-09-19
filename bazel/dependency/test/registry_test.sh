#!/bin/bash

set -euo pipefail

JQ="${JQ_BIN:-jq}"

if ! command -v git >/dev/null 2>&1; then
    echo "Skipping registry_test: git not available"
    exit 0
fi

if [ -n "${TEST_SRCDIR:-}" ]; then
    if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
        RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
    else
        RUNFILES_DIR="${TEST_SRCDIR}/_main"
    fi
    REGISTRY_BIN="${RUNFILES_DIR}/dependency/test/registry"
    FIXTURE_ROOT="${RUNFILES_DIR}/dependency/test/testdata/registry/workspace"
    REGISTRY_PATHS_JSON=""
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REGISTRY_BIN="$(cd "${SCRIPT_DIR}/.." && pwd)/registry.sh"
    FIXTURE_ROOT="${SCRIPT_DIR}/testdata/registry/workspace"
    REGISTRY_PATHS_JSON='{"bazelrc":["dependency/test/testdata/registry/workspace/.bazelrc","dependency/test/testdata/registry/workspace/api/.bazelrc"],"modules":["dependency/test/testdata/registry/workspace/MODULE.bazel","dependency/test/testdata/registry/workspace/api/MODULE.bazel"],"version":"dependency/test/testdata/registry/workspace/VERSION.txt"}'
fi

run_registry() {
    if [[ -n "${REGISTRY_PATHS_JSON}" ]]; then
        BUILD_WORKSPACE_DIRECTORY="$1" \
            JQ_BIN="${JQ}" \
            REGISTRY_PATHS_JSON="${REGISTRY_PATHS_JSON}" \
            "${REGISTRY_BIN}" "${@:2}"
    else
        BUILD_WORKSPACE_DIRECTORY="$1" \
            "${REGISTRY_BIN}" "${@:2}"
    fi
}

make_registry_repo() {
    local repo_root="$1"
    local worktree="${repo_root}/worktree"
    local bare_repo="${repo_root}/registry.git"
    local old_hash
    local new_hash

    git init --quiet --initial-branch=main "${worktree}"
    git -C "${worktree}" config user.name 'Toolshed Test'
    git -C "${worktree}" config user.email 'toolshed@example.com'
    mkdir -p "${worktree}/modules/foo/1.0.0-20240101" "${worktree}/modules/foo/1.1.0-20250101"
    cat > "${worktree}/modules/foo/metadata.json" <<'EOF'
{"versions":["1.0.0-20240101","1.1.0-20250101"]}
EOF
    cat > "${worktree}/modules/foo/1.0.0-20240101/MODULE.bazel" <<'EOF'
module(name = "foo")
EOF
    cat > "${worktree}/modules/foo/1.1.0-20250101/MODULE.bazel" <<'EOF'
module(name = "foo")
EOF
    git -C "${worktree}" add modules
    git -C "${worktree}" commit --quiet -m 'initial registry'
    git -C "${worktree}" tag v0.1.0
    old_hash="$(git -C "${worktree}" rev-parse HEAD)"

    rm -rf "${worktree}/modules/foo/1.0.0-20240101"
    cat > "${worktree}/modules/foo/metadata.json" <<'EOF'
{"versions":["1.1.0-20250101"]}
EOF
    git -C "${worktree}" add modules
    git -C "${worktree}" commit --quiet -m 'remove old foo pin'
    new_hash="$(git -C "${worktree}" rev-parse HEAD)"

    git clone --quiet --bare "${worktree}" "${bare_repo}"

    printf '%s\n%s\n%s\n' "${old_hash}" "${new_hash}" "${bare_repo}"
}

copy_workspace_fixture() {
    local workspace_root="$1"

    mkdir -p "${workspace_root}/dependency/test/testdata/registry/workspace"
    cp -R "${FIXTURE_ROOT}/." "${workspace_root}/dependency/test/testdata/registry/workspace"
}

assert_eq() {
    local expected="$1"
    local actual="$2"
    local message="$3"

    if [[ "${expected}" != "${actual}" ]]; then
        echo "FAIL: ${message}" >&2
        echo "expected: ${expected}" >&2
        echo "actual:   ${actual}" >&2
        exit 1
    fi
}

run_dry_run_test() {
    local temp_root
    temp_root="$(mktemp -d)"
    local repo_root="${temp_root}/repo"
    mkdir -p "${repo_root}"

    mapfile -t repo_info < <(make_registry_repo "${repo_root}")
    local old_hash="${repo_info[0]}"
    local new_hash="${repo_info[1]}"
    local bare_repo="${repo_info[2]}"
    local workspace_root="${temp_root}/workspace"
    local report_path="${temp_root}/report.json"
    local before_hashes
    local after_hashes

    copy_workspace_fixture "${workspace_root}"
    sed -i "s/OLD_REGISTRY_HASH/${old_hash}/g" \
        "${workspace_root}/dependency/test/testdata/registry/workspace/.bazelrc" \
        "${workspace_root}/dependency/test/testdata/registry/workspace/api/.bazelrc"
    before_hashes="$(find "${workspace_root}" -type f | sort | xargs sha256sum)"

    run_registry "${workspace_root}" \
        --repo "${bare_repo}" \
        --dry-run \
        --output "${report_path}" >"${temp_root}/registry-dry-run.log"

    after_hashes="$(find "${workspace_root}" -type f | sort | xargs sha256sum)"
    assert_eq "${before_hashes}" "${after_hashes}" "dry-run modified workspace files"
    assert_eq "${new_hash}" "$("${JQ}" -r '.registry.new' "${report_path}")" "dry-run report new hash"
    assert_eq "${old_hash}" "$("${JQ}" -r '.registry.old' "${report_path}")" "dry-run report old hash"
    assert_eq "foo" "$("${JQ}" -r '.modules[0].name' "${report_path}")" "dry-run updated module name"
    assert_eq "1.1.0-20250101" "$("${JQ}" -r '.modules[0].to' "${report_path}")" "dry-run replacement version"
    rm -rf "${temp_root}"
}

run_write_test() {
    local temp_root
    temp_root="$(mktemp -d)"
    local repo_root="${temp_root}/repo"
    mkdir -p "${repo_root}"

    mapfile -t repo_info < <(make_registry_repo "${repo_root}")
    local old_hash="${repo_info[0]}"
    local new_hash="${repo_info[1]}"
    local bare_repo="${repo_info[2]}"
    local workspace_root="${temp_root}/workspace"
    local report_path="${temp_root}/report.json"

    copy_workspace_fixture "${workspace_root}"
    sed -i "s/OLD_REGISTRY_HASH/${old_hash}/g" \
        "${workspace_root}/dependency/test/testdata/registry/workspace/.bazelrc" \
        "${workspace_root}/dependency/test/testdata/registry/workspace/api/.bazelrc"

    run_registry "${workspace_root}" \
        --repo "${bare_repo}" \
        --output "${report_path}" >"${temp_root}/registry-write.log"

    grep -q "${new_hash}" "${workspace_root}/dependency/test/testdata/registry/workspace/.bazelrc"
    grep -q "${new_hash}" "${workspace_root}/dependency/test/testdata/registry/workspace/api/.bazelrc"
    grep -q 'version = "1.1.0-20250101"' "${workspace_root}/dependency/test/testdata/registry/workspace/MODULE.bazel"
    grep -q 'version = "1.1.0-20250101"' "${workspace_root}/dependency/test/testdata/registry/workspace/api/MODULE.bazel"
    grep -q $'\tkeep-tab' "${workspace_root}/dependency/test/testdata/registry/workspace/MODULE.bazel"
    assert_eq "${new_hash}" "$("${JQ}" -r '.registry.new' "${report_path}")" "write report new hash"
    rm -rf "${temp_root}"
}

run_cli_error_test() {
    local temp_root
    temp_root="$(mktemp -d)"
    local workspace_root="${temp_root}/workspace"
    mkdir -p "${workspace_root}"
    copy_workspace_fixture "${workspace_root}"

    if run_registry "${workspace_root}" --check-only --skip-check >"${temp_root}/registry-invalid.log" 2>"${temp_root}/registry-invalid.err"; then
        echo "FAIL: expected --check-only --skip-check to fail" >&2
        exit 1
    fi
    grep -q '^FAIL: --skip-check is invalid with --check-only$' "${temp_root}/registry-invalid.err"
    rm -rf "${temp_root}"
}

run_dry_run_test
run_write_test
run_cli_error_test
