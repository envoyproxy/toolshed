#!/bin/bash

set -euo pipefail

usage() {
    cat <<'EOUSAGE'
Usage:
  registry-resolve.sh resolve --repo=<repo> --url=<url> --branch=<branch> [--release-tags=<glob>] [--requested-sha=<sha>] [--allow-unsafe] [--format=json|markdown] [--json-out=<path>] [--markdown-out=<path>] [--sha-out=<path>] [--git-bin=<path>] [--jq-bin=<path>] [--jq-root=<path>]
  registry-resolve.sh check --repo=<repo> --url=<url> --branch=<branch> --bazelrc=<path> [--allow-unsafe] [--format=json|markdown] [--json-out=<path>] [--markdown-out=<path>] [--sha-out=<path>] [--git-bin=<path>] [--jq-bin=<path>] [--jq-root=<path>]
EOUSAGE
}

fail() {
    echo "$1" >&2
    exit "${2:-1}"
}

warn() {
    echo "WARNING: $1" >&2
}

normalize_bool() {
    case "$1" in
        1|true|True|TRUE|yes|YES|on|ON) echo true ;;
        0|false|False|FALSE|no|NO|off|OFF|'') echo false ;;
        *) fail "invalid boolean value: $1" 1 ;;
    esac
}

run_jq() {
    "$JQ_BIN" -L "$JQ_DIR" "$@"
}

git_cmd() {
    HOME="$GIT_HOME" GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 "$GIT_BIN" -c safe.bareRepository=all "$@"
}

normalize_sha() {
    printf '%s\n' "$1" | run_jq -Rr 'import "bazel/registry" as registry; registry::normalize_sha'
}

require_requested_sha() {
    local sha

    if sha="$(normalize_sha "$1" 2>/dev/null)"; then
        printf '%s\n' "$sha"
        return
    fi

    fail "registry SHA must be a full 40-character hex commit" 2
}

read_bazelrc_sha() {
    local bazelrc="$1"
    local message
    local sha

    if sha="$(run_jq -Rrs --arg url "$URL" -r 'import "bazel/registry" as registry; registry::bazelrc_pin_from_args' < "$bazelrc")"; then
        printf '%s\n' "$sha"
        return
    fi

    message="$(run_jq -Rrs --arg url "$URL" 'import "bazel/registry" as registry; try registry::bazelrc_pin_from_args catch .' < "$bazelrc")"
    fail "${message} in ${bazelrc}" 2
}

collect_latest() {
    local latest

    latest="$(git_cmd ls-remote --exit-code "$REPO" "refs/heads/$BRANCH" | run_jq -Rrsc 'import "bazel/registry" as registry; registry::ls_remote_head')"
    LATEST="$(normalize_sha "$latest" 2>/dev/null)" || fail "expected 40-hex commit for ${REPO} refs/heads/${BRANCH}, got '${latest}'" 1
}

collect_tags() {
    TAGS_JSON="$(git_cmd ls-remote --tags "$REPO" | run_jq -Rsc 'import "bazel/registry" as registry; registry::ls_remote_tags')"
}

select_target() {
    if [[ -n "$REQUESTED_SHA" ]]; then
        TARGET_SHA="$(require_requested_sha "$REQUESTED_SHA")"
        return
    fi

    if [[ -z "$RELEASE_TAGS" ]]; then
        TARGET_SHA="$LATEST"
        return
    fi

    if ! TARGET_SHA="$(printf '%s\n' "$TAGS_JSON" | run_jq --arg glob "$RELEASE_TAGS" -r 'import "bazel/registry" as registry; registry::select_release_sha_from_args')"; then
        fail "No registry tag matches ${RELEASE_TAGS}" 2
    fi
}

collect_target_tags() {
    TARGET_TAGS_JSON="$(printf '%s\n' "$TAGS_JSON" | run_jq --arg sha "$TARGET_SHA" -c 'import "bazel/registry" as registry; registry::tags_for_from_args')"
}

verify_target() {
    local bare_repo="$TMPDIR_ROOT/verify.git"

    ANCESTOR=true
    BEHIND=0
    if [[ "$TARGET_SHA" == "$LATEST" ]]; then
        return
    fi

    git_cmd init --bare "$bare_repo" >/dev/null
    git_cmd -C "$bare_repo" fetch --filter=tree:0 --no-tags "$REPO" "refs/heads/$BRANCH" >/dev/null
    if ! git_cmd -C "$bare_repo" cat-file -e "${TARGET_SHA}^{commit}" >/dev/null 2>&1 || \
        ! git_cmd -C "$bare_repo" merge-base --is-ancestor "$TARGET_SHA" FETCH_HEAD >/dev/null 2>&1; then
        ANCESTOR=false
        BEHIND=null
        if [[ "$ALLOW_UNSAFE" == "true" ]]; then
            warn "registry SHA ${TARGET_SHA} is not an ancestor of ${BRANCH}; continuing because allow_unsafe is set"
            return
        fi
        fail "registry SHA ${TARGET_SHA} is not an ancestor of ${BRANCH}" 2
    fi

    if [[ "$MODE" == "check" ]]; then
        BEHIND="$(git_cmd -C "$bare_repo" rev-list --count "${TARGET_SHA}..FETCH_HEAD")"
    fi
}

emit_output() {
    local output
    local markdown

    if [[ "$MODE" == "resolve" ]]; then
        output="$(run_jq -n \
            --arg sha "$TARGET_SHA" \
            --arg url "$URL" \
            --arg branch "$BRANCH" \
            --arg latest "$LATEST" \
            --arg requested "$REQUESTED_SHA" \
            --argjson ancestor "$ANCESTOR" \
            --argjson tags "$TARGET_TAGS_JSON" \
            --argjson unsafe "$ALLOW_UNSAFE" \
            'import "bazel/registry" as registry; registry::resolve_output_from_args')"
    else
        output="$(run_jq -n \
            --arg sha "$TARGET_SHA" \
            --arg latest "$LATEST" \
            --argjson ancestor "$ANCESTOR" \
            --argjson tags "$TARGET_TAGS_JSON" \
            --argjson behind "$BEHIND" \
            'import "bazel/registry" as registry; registry::check_output_from_args')"
    fi

    if [[ -n "$SHA_OUT" ]]; then
        printf '%s\n' "$TARGET_SHA" > "$SHA_OUT"
    fi

    markdown=""
    if [[ -n "$MARKDOWN_OUT" || "$FORMAT" == markdown ]]; then
        markdown="$(printf '%s\n' "$output" | run_jq -r 'import "bazel/registry" as registry; registry::check_markdown')"
        if [[ -n "$MARKDOWN_OUT" ]]; then
            printf '%s\n' "$markdown" > "$MARKDOWN_OUT"
        fi
    fi

    if [[ -n "$JSON_OUT" ]]; then
        printf '%s\n' "$output" > "$JSON_OUT"
    fi

    if [[ "$FORMAT" == markdown ]]; then
        printf '%s\n' "$markdown"
    elif [[ -z "$JSON_OUT" ]]; then
        printf '%s\n' "$output"
    fi
}

MODE=""
REPO=""
URL=""
BRANCH=""
RELEASE_TAGS=""
REQUESTED_SHA=""
ALLOW_UNSAFE=false
BAZELRC=""
FORMAT=json
JSON_OUT=""
MARKDOWN_OUT=""
SHA_OUT=""
SETTINGS_FILE=""
GIT_BIN="${GIT_BIN:-git}"
JQ_BIN="${JQ_BIN:-jq}"
JQ_ROOT="${TOOLSHED_JQ_ROOT:-}"

[[ $# -gt 0 ]] || {
    usage >&2
    exit 1
}
MODE="$1"
shift

while (($#)); do
    case "$1" in
        --repo=*) REPO="${1#*=}" ;;
        --repo) REPO="$2"; shift ;;
        --url=*) URL="${1#*=}" ;;
        --url) URL="$2"; shift ;;
        --branch=*) BRANCH="${1#*=}" ;;
        --branch) BRANCH="$2"; shift ;;
        --release-tags=*) RELEASE_TAGS="${1#*=}" ;;
        --release-tags) RELEASE_TAGS="$2"; shift ;;
        --requested-sha=*) REQUESTED_SHA="${1#*=}" ;;
        --requested-sha) REQUESTED_SHA="$2"; shift ;;
        --allow-unsafe) ALLOW_UNSAFE=true ;;
        --allow-unsafe=*) ALLOW_UNSAFE="$(normalize_bool "${1#*=}")" ;;
        --bazelrc=*) BAZELRC="${1#*=}" ;;
        --bazelrc) BAZELRC="$2"; shift ;;
        --format=*) FORMAT="${1#*=}" ;;
        --format) FORMAT="$2"; shift ;;
        --json-out=*) JSON_OUT="${1#*=}" ;;
        --json-out) JSON_OUT="$2"; shift ;;
        --markdown-out=*) MARKDOWN_OUT="${1#*=}" ;;
        --markdown-out) MARKDOWN_OUT="$2"; shift ;;
        --sha-out=*) SHA_OUT="${1#*=}" ;;
        --sha-out) SHA_OUT="$2"; shift ;;
        --settings-file=*) SETTINGS_FILE="${1#*=}" ;;
        --settings-file) SETTINGS_FILE="$2"; shift ;;
        --git-bin=*) GIT_BIN="${1#*=}" ;;
        --git-bin) GIT_BIN="$2"; shift ;;
        --jq-bin=*) JQ_BIN="${1#*=}" ;;
        --jq-bin) JQ_BIN="$2"; shift ;;
        --jq-root=*) JQ_ROOT="${1#*=}" ;;
        --jq-root) JQ_ROOT="$2"; shift ;;
        --help|-h) usage; exit 0 ;;
        *) fail "Unknown option: $1" 1 ;;
    esac
    shift
 done

case "$MODE" in
    resolve|check) ;;
    *) usage >&2; exit 1 ;;
esac

case "$FORMAT" in
    json|markdown) ;;
    *) fail "Unknown format: $FORMAT" 1 ;;
esac

[[ -n "$REPO" ]] || fail "--repo is required" 1
[[ -n "$URL" ]] || fail "--url is required" 1
[[ -n "$BRANCH" ]] || fail "--branch is required" 1
if [[ "$MODE" == "check" ]]; then
    [[ -n "$BAZELRC" ]] || fail "--bazelrc is required for check" 1
fi

TMPDIR_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_ROOT"' EXIT
GIT_HOME="$TMPDIR_ROOT/git-home"
mkdir -p "$GIT_HOME"
JQ_DIR="$(dirname "${JQ_ROOT:?--jq-root is required}")"
TARGET_TAGS_JSON='[]'
LATEST=""
TARGET_SHA=""
TAGS_JSON='{}'
ANCESTOR=true
BEHIND=0

if [[ -n "$SETTINGS_FILE" ]]; then
    [[ -f "$SETTINGS_FILE" ]] || fail "settings file not found: $SETTINGS_FILE" 1
    if [[ -z "$REQUESTED_SHA" ]]; then
        REQUESTED_SHA="$("$JQ_BIN" -r '.requested_sha // ""' "$SETTINGS_FILE")"
    fi
    if [[ "$ALLOW_UNSAFE" == "false" ]]; then
        ALLOW_UNSAFE="$(normalize_bool "$("$JQ_BIN" -r '.allow_unsafe // false' "$SETTINGS_FILE")")"
    fi
fi

if [[ -n "$REQUESTED_SHA" ]]; then
    REQUESTED_SHA="$(require_requested_sha "$REQUESTED_SHA")"
fi

if [[ "$MODE" == "check" ]]; then
    REQUESTED_SHA="$(read_bazelrc_sha "$BAZELRC")"
fi

collect_latest
collect_tags
select_target
collect_target_tags
verify_target
emit_output
