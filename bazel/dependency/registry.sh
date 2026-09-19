#!/usr/bin/env bash
# shellcheck disable=SC2016

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIRECTORY="${BUILD_WORKSPACE_DIRECTORY:-$(pwd)}"
REGISTRY_PATHS_JSON="${REGISTRY_PATHS_JSON:-}"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

_resolve_runfile() {
    local value="$1"
    if [[ -n "$value" && "$value" != /* ]]; then
        local f=bazel_tools/tools/bash/runfiles/runfiles.bash
        if [[ -z "${RUNFILES_DIR:-}" && -n "${TEST_SRCDIR:-}" ]]; then
            RUNFILES_DIR="${TEST_SRCDIR}"
        fi
        local runfiles_bash_path="${RUNFILES_DIR:-/dev/null}/$f"
        # shellcheck disable=SC1090
        source "${runfiles_bash_path}" 2>/dev/null || \
            source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2 -d' ')" 2>/dev/null || \
            { echo >&2 "FAIL: cannot find runfiles.bash"; exit 1; }
        rlocation "${value}"
    else
        printf '%s\n' "${value}"
    fi
}

if [[ -n "${JQ_BIN:-}" ]]; then
    JQ_BIN="$(_resolve_runfile "${JQ_BIN}")"
fi
JQ="${JQ_BIN:-jq}"
if ! command -v "${JQ}" >/dev/null 2>&1; then
    fail "jq binary not found: ${JQ}"
fi

if [[ -n "${JQ_MODULES_ROOT_MARKER:-}" ]]; then
    JQ_LIBDIR="$(dirname "$(_resolve_runfile "${JQ_MODULES_ROOT_MARKER}")")"
else
    JQ_LIBDIR="$(cd "${SCRIPT_DIR}/../../jq" && pwd)"
fi

jq_registry() {
    "${JQ}" -L "${JQ_LIBDIR}" "$@"
}

print_json_lines() {
    jq_registry -r "$2" <<<"$1"
}

collect_files_json() {
    local paths_json="$1"
    local result='{}'
    local path
    local content_json

    while IFS= read -r path; do
        content_json="$(jq_registry -Rs --arg path "${path}" '{($path): .}' < "${WORKSPACE_DIRECTORY}/${path}")"
        result="$(jq_registry -n \
            --argjson result "${result}" \
            --argjson content "${content_json}" \
            '$result + $content')"
    done < <(jq_registry -nr --argjson paths "${paths_json}" '$paths[]')

    printf '%s' "${result}"
}

write_updates() {
    local updates_json="$1"
    local entry
    local path

    while IFS= read -r entry; do
        path="$(jq_registry -r '.path' <<<"${entry}")"
        mkdir -p "$(dirname "${WORKSPACE_DIRECTORY}/${path}")"
        jq_registry -rj '.content' <<<"${entry}" > "${WORKSPACE_DIRECTORY}/${path}"
    done < <(jq_registry -nc --argjson updates "${updates_json}" '$updates | to_entries[] | {path: .key, content: .value}')
}

if [[ -z "${REGISTRY_PATHS_JSON}" ]]; then
    fail "REGISTRY_PATHS_JSON is required"
fi

config="$(jq_registry -n 'include "registry"; parse_args' --args -- "$@")"
if [[ "$(print_json_lines "${config}" '.errors | length')" != "0" ]]; then
    print_json_lines "${config}" '.errors[]' >&2
    exit 1
fi

repo="$(print_json_lines "${config}" '.repo')"
branch="$(print_json_lines "${config}" '.branch')"
output_path="$(print_json_lines "${config}" '.output')"
skip_check="$(print_json_lines "${config}" '.skip_check')"
check_only="$(print_json_lines "${config}" '.check_only')"
dry_run="$(print_json_lines "${config}" '.dry_run')"
overrides="$(jq_registry -c '.overrides' <<<"${config}")"
url_prefix="${REGISTRY_URL_PREFIX:-https://raw.githubusercontent.com/envoyproxy/bazel-registry/}"
bazelrc_paths="$(jq_registry -nc --argjson paths "${REGISTRY_PATHS_JSON}" '$paths.bazelrc')"
module_paths="$(jq_registry -nc --argjson paths "${REGISTRY_PATHS_JSON}" '$paths.modules')"
version_file="$(jq_registry -nr --argjson paths "${REGISTRY_PATHS_JSON}" '$paths.version')"

bazelrc_files="$(collect_files_json "${bazelrc_paths}")"
module_files_json="$(collect_files_json "${module_paths}")"
version_text="$(<"${WORKSPACE_DIRECTORY}/${version_file}")"

old_hash_result="$(jq_registry -n \
    --argjson files "${bazelrc_files}" \
    --argjson paths "${bazelrc_paths}" \
    --arg url_prefix "${url_prefix}" \
    'include "registry"; {files: $files, paths: $paths, url_prefix: $url_prefix} | bazelrc_hash')"
old_hash="$(print_json_lines "${old_hash_result}" '.hash // empty')"
if [[ -z "${old_hash}" ]]; then
    fail "$(print_json_lines "${old_hash_result}" '.error')"
fi

new_hash="$(print_json_lines "${config}" '.hash // empty')"
if [[ -z "${new_hash}" ]]; then
    if ! ls_remote_output="$(git ls-remote "${repo}" "refs/heads/${branch}" 2>&1)"; then
        fail "${ls_remote_output}"
    fi
    new_hash="$(jq_registry -nr --arg output "${ls_remote_output}" 'include "registry"; $output | ls_remote_hash')"
    if [[ -z "${new_hash}" ]]; then
        fail "Failed to determine bazel-registry hash from ${repo} ${branch}"
    fi
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

if ! clone_output="$(git clone --quiet --bare --filter=blob:none "${repo}" "${tmpdir}/registry.git" 2>&1)"; then
    fail "${clone_output}"
fi

git_registry() {
    git -c safe.bareRepository=all -C "${tmpdir}/registry.git" "$@"
}

target_hash="${new_hash}"
if [[ "${check_only}" == "true" ]]; then
    target_hash="${old_hash}"
fi

commit_exists=false
if git_registry cat-file -e "${target_hash}^{commit}" >/dev/null 2>&1; then
    commit_exists=true
fi

is_ancestor=false
if git_registry merge-base --is-ancestor "${target_hash}" "${branch}" >/dev/null 2>&1; then
    is_ancestor=true
fi

tags="$(git_registry tag --points-at "${target_hash}" || true)"
check_result="$(jq_registry -n \
    --arg hash "${target_hash}" \
    --arg version_txt "${version_text}" \
    --arg branch "${branch}" \
    --arg repo "${repo}" \
    --arg tags "${tags}" \
    --argjson exists_commit "${commit_exists}" \
    --argjson is_ancestor "${is_ancestor}" \
    --argjson skip_check "${skip_check}" \
    'include "registry";
     {
       hash: $hash,
       exists_commit: $exists_commit,
       is_ancestor: $is_ancestor,
       tags: ($tags | split("\n") | map(select(length > 0))),
       version_txt: $version_txt,
       branch: $branch,
       repo: $repo,
       skip_check: $skip_check,
     } | check')"
print_json_lines "${check_result}" '.messages[]?'
if [[ "$(print_json_lines "${check_result}" '.errors | length')" != "0" ]]; then
    print_json_lines "${check_result}" '.errors[]' >&2
    exit 1
fi

if [[ "${check_only}" == "true" ]]; then
    exit 0
fi

pins="$(jq_registry -n \
    --argjson files "${module_files_json}" \
    --argjson paths "${module_paths}" \
    'include "registry"; {files: $files, paths: $paths} | module_pins')"
object_paths="$(jq_registry -n --argjson pins "${pins}" 'include "registry"; {pins: $pins} | registry_objects')"

batch_input=""
while IFS= read -r path; do
    batch_input+="${new_hash}:${path} ${path}"$'\n'
done < <(print_json_lines "${object_paths}" '.[]')

exists_json='{}'
if [[ -n "${batch_input}" ]]; then
    exists_json="$(printf '%s' "${batch_input}" \
        | git_registry cat-file --batch-check='%(rest) %(objecttype)' \
        | jq_registry -Rs 'include "registry"; batch_check_exists')"
fi

metadata='{}'
while IFS= read -r module_name; do
    metadata="$(jq_registry -n \
        --argjson metadata "${metadata}" \
        --arg name "${module_name}" \
        --argjson value "$(git_registry show "${new_hash}:modules/${module_name}/metadata.json")" \
        '$metadata + {($name): $value}')"
done < <(jq_registry -nr \
    --argjson pins "${pins}" \
    --argjson exists "${exists_json}" \
    'include "registry"; {pins: $pins, exists: $exists} | metadata_modules[]')

plan="$(jq_registry -n \
    --argjson pins "${pins}" \
    --argjson exists "${exists_json}" \
    --argjson metadata "${metadata}" \
    --argjson overrides "${overrides}" \
    --arg old_hash "${old_hash}" \
    --arg new_hash "${new_hash}" \
    'include "registry";
     {
       pins: $pins,
       exists: $exists,
       metadata: $metadata,
       overrides: $overrides,
       old_hash: $old_hash,
       new_hash: $new_hash,
     } | plan')"
if [[ "$(print_json_lines "${plan}" '.errors | length')" != "0" ]]; then
    print_json_lines "${plan}" '.errors[]' >&2
    exit 1
fi

if [[ "${dry_run}" != "true" ]]; then
    hash_updates="$(jq_registry -n \
        --argjson files "${bazelrc_files}" \
        --argjson paths "${bazelrc_paths}" \
        --arg url_prefix "${url_prefix}" \
        --arg hash "${new_hash}" \
        'include "registry"; {files: $files, paths: $paths, url_prefix: $url_prefix, hash: $hash} | apply_hash')"
    edit_updates="$(jq_registry -n \
        --argjson files "${module_files_json}" \
        --argjson edits "$(jq_registry -c '.edits' <<<"${plan}")" \
        'include "registry"; {files: $files, edits: $edits} | apply_edits')"
    write_updates "$(jq_registry -nc \
        --argjson hash_updates "${hash_updates}" \
        --argjson edit_updates "${edit_updates}" \
        '$hash_updates + $edit_updates')"
fi

if [[ "${output_path}" != /* ]]; then
    output_path="${WORKSPACE_DIRECTORY}/${output_path}"
fi
mkdir -p "$(dirname "${output_path}")"
jq_registry 'del(.edits, .errors)' <<<"${plan}" > "${output_path}"
jq_registry -r 'include "registry"; render_report' <<<"${plan}"
