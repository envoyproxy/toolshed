#!/bin/bash

set -euo pipefail

usage() {
    cat <<'EOUSAGE'
Usage:
  registry-resolve.sh resolve --repo=<repo> --url=<url> --branch=<branch> [--release-tags=<glob>] [--requested-sha=<sha>] [--allow-unsafe] [--json-out=<path>] [--git-bin=<path>] [--jq-bin=<path>] [--jq-lib=<path>]
  registry-resolve.sh check --repo=<repo> --url=<url> --branch=<branch> --bazelrc=<path> [--allow-unsafe] [--json-out=<path>] [--git-bin=<path>] [--jq-bin=<path>] [--jq-lib=<path>] [--cache-ttl=<seconds>]
EOUSAGE
}

fail() {
    echo "$1" >&2
    exit "${2:-1}"
}

warn() {
    echo "WARNING: $1" >&2
}

require_full_sha() {
    local sha="$1"

    if [[ -n "$sha" && ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
        fail "registry SHA must be a full 40-character lowercase hex commit" 2
    fi
}

require_integer() {
    local value="$1"
    local name="$2"

    if [[ ! "$value" =~ ^[0-9]+$ ]]; then
        fail "${name} must be a non-negative integer" 1
    fi
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

stable_cache_root() {
    if [[ -n "${XDG_CACHE_HOME:-}" ]]; then
        printf '%s/envoy_toolshed/registry\n' "$XDG_CACHE_HOME"
    elif [[ -n "${ORIGINAL_HOME:-}" ]]; then
        printf '%s/.cache/envoy_toolshed/registry\n' "$ORIGINAL_HOME"
    else
        printf '%s/envoy_toolshed/registry\n' "$TMPDIR_ROOT"
    fi
}

file_mtime() {
    if stat -c '%Y' "$1" >/dev/null 2>&1; then
        stat -c '%Y' "$1"
        return
    fi
    stat -f '%m' "$1"
}

cache_key() {
    {
        printf 'mode=%s\n' "$MODE"
        printf 'repo=%s\n' "$REPO"
        printf 'url=%s\n' "$URL"
        printf 'branch=%s\n' "$BRANCH"
        printf 'release_tags=%s\n' "$RELEASE_TAGS"
        printf 'requested_sha=%s\n' "$REQUESTED_SHA"
        printf 'allow_unsafe=%s\n' "$ALLOW_UNSAFE"
        printf 'current_sha=%s\n' "$CURRENT_SHA"
    } | cksum | awk '{print $1 "-" $2}'
}

read_cache() {
    local ttl="$1"
    local path="$2"
    local now
    local mtime

    [[ -f "$path" ]] || return 1
    now="$(date +%s)"
    mtime="$(file_mtime "$path")"
    if (( now - mtime >= ttl )); then
        return 1
    fi
    cat "$path"
}

write_cache() {
    local path="$1"
    local content="$2"

    mkdir -p "$(dirname "$path")"
    printf '%s\n' "$content" > "$path"
}

escape_regex() {
    printf '%s' "$1" | sed -e 's/[][(){}.^$*+?|\\]/\\&/g'
}

read_bazelrc_sha() {
    local bazelrc="$1"
    local prefix_re
    local matches
    local count

    prefix_re="$(escape_regex "$URL")"
    matches="$TMPDIR_ROOT/bazelrc_matches.txt"
    awk -v prefix_re="$prefix_re" '
        $0 ~ "^[A-Za-z0-9_:-]* --registry=" prefix_re "/[0-9a-f]{40}[[:space:]]*$" {
            sub("^[A-Za-z0-9_:-]* --registry=" prefix_re "/", "", $0)
            sub("[[:space:]]*$", "", $0)
            print
        }
    ' "$bazelrc" | sort -u > "$matches"
    count="$(wc -l < "$matches" | tr -d ' ')"
    if [[ "$count" == "0" ]]; then
        fail "No '--registry=${URL}/<sha>' line found in ${bazelrc}" 2
    fi
    if [[ "$count" != "1" ]]; then
        fail "Found multiple differing '--registry=${URL}/<sha>' pins in ${bazelrc}" 2
    fi
    cat "$matches"
}

collect_latest() {
    LATEST="$(git_cmd ls-remote --exit-code "$REPO" "refs/heads/$BRANCH" | awk 'NR == 1 {print $1}')"
    if [[ ! "$LATEST" =~ ^[0-9a-f]{40}$ ]]; then
        fail "expected 40-hex commit for ${REPO} refs/heads/${BRANCH}, got '${LATEST}'" 1
    fi
}

collect_tags() {
    local raw_tags="$TMPDIR_ROOT/tags.raw"

    git_cmd ls-remote --tags "$REPO" > "$raw_tags"
    awk '
        {
            ref = $2
            sub(/^refs\/tags\//, "", ref)
            peeled = sub(/\^\{\}$/, "", ref)
            if (!(ref in seen)) {
                seen[ref] = 1
                order[++count] = ref
            }
            if (!(ref in sha) || peeled) {
                sha[ref] = $1
            }
        }
        END {
            for (i = 1; i <= count; i++) {
                ref = order[i]
                if (sha[ref] != "") {
                    print ref "\t" sha[ref]
                }
            }
        }
    ' "$raw_tags" > "$TAGS_FILE"
}

select_target() {
    local matches="$TMPDIR_ROOT/tag_matches.txt"
    local selected_tag

    if [[ -n "$REQUESTED_SHA" ]]; then
        TARGET_SHA="$REQUESTED_SHA"
        return
    fi

    if [[ -z "$RELEASE_TAGS" ]]; then
        TARGET_SHA="$LATEST"
        return
    fi

    : > "$matches"
    while IFS=$'\t' read -r tag sha; do
        [[ -n "$tag" ]] || continue
        case "$tag" in
            $RELEASE_TAGS)
                printf '%s\n' "$tag" >> "$matches"
                ;;
        esac
    done < "$TAGS_FILE"

    if [[ ! -s "$matches" ]]; then
        fail "No registry tag matches ${RELEASE_TAGS}" 2
    fi

    selected_tag="$(run_jq -Rsc -r -f "$JQ_DIR/registry_select_tag.jq" < "$matches")"
    [[ -n "$selected_tag" ]] || fail "No registry tag matches ${RELEASE_TAGS}" 2
    TARGET_SHA="$(awk -F '\t' -v selected="$selected_tag" '$1 == selected {print $2; exit}' "$TAGS_FILE")"
    [[ -n "$TARGET_SHA" ]] || fail "No SHA found for registry tag ${selected_tag}" 1
}

collect_target_tags() {
    TARGET_TAGS_JSON="$(awk -F '\t' -v sha="$TARGET_SHA" '$2 == sha {print $1}' "$TAGS_FILE" | run_jq -Rsc -f "$JQ_DIR/registry_tags_array.jq")"
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

emit_json() {
    local filter="$1"
    local output

    output="$(run_jq -n \
        --arg sha "$TARGET_SHA" \
        --arg url "$URL" \
        --arg branch "$BRANCH" \
        --arg latest "$LATEST" \
        --arg requested "$REQUESTED_SHA" \
        --argjson ancestor "$ANCESTOR" \
        --argjson tags "$TARGET_TAGS_JSON" \
        --argjson unsafe "$ALLOW_UNSAFE" \
        --arg behind "$BEHIND" \
        -f "$filter")"

    if [[ -n "$JSON_OUT" ]]; then
        printf '%s\n' "$output" > "$JSON_OUT"
    else
        printf '%s\n' "$output"
    fi

    if [[ "$CACHE_TTL" != "0" ]]; then
        write_cache "$CACHE_FILE" "$output"
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
JSON_OUT=""
CACHE_TTL=0
SETTINGS_FILE=""
GIT_BIN="${GIT_BIN:-git}"
JQ_BIN="${JQ_BIN:-jq}"
JQ_LIB="${REGISTRY_JQ_LIB:-}"
ORIGINAL_HOME="${HOME:-}"

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
        --json-out=*) JSON_OUT="${1#*=}" ;;
        --json-out) JSON_OUT="$2"; shift ;;
        --cache-ttl=*) CACHE_TTL="${1#*=}" ;;
        --cache-ttl) CACHE_TTL="$2"; shift ;;
        --settings-file=*) SETTINGS_FILE="${1#*=}" ;;
        --settings-file) SETTINGS_FILE="$2"; shift ;;
        --git-bin=*) GIT_BIN="${1#*=}" ;;
        --git-bin) GIT_BIN="$2"; shift ;;
        --jq-bin=*) JQ_BIN="${1#*=}" ;;
        --jq-bin) JQ_BIN="$2"; shift ;;
        --jq-lib=*) JQ_LIB="${1#*=}" ;;
        --jq-lib) JQ_LIB="$2"; shift ;;
        --help|-h) usage; exit 0 ;;
        *) fail "Unknown option: $1" 1 ;;
    esac
    shift
 done

case "$MODE" in
    resolve|check) ;;
    *) usage >&2; exit 1 ;;
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
TAGS_FILE="$TMPDIR_ROOT/tags.tsv"
JQ_DIR="$(dirname "${JQ_LIB:?--jq-lib is required}")"
CURRENT_SHA=""
TARGET_SHA=""
TARGET_TAGS_JSON='[]'
LATEST=""
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
    if [[ "$CACHE_TTL" == "0" ]]; then
        CACHE_TTL="$("$JQ_BIN" -r '.cache_ttl // "0"' "$SETTINGS_FILE")"
    fi
fi

require_integer "$CACHE_TTL" "cache TTL"
require_full_sha "$REQUESTED_SHA"

if [[ "$MODE" == "check" ]]; then
    CURRENT_SHA="$(read_bazelrc_sha "$BAZELRC")"
    REQUESTED_SHA="$CURRENT_SHA"
fi

CACHE_FILE=""
if [[ "$CACHE_TTL" != "0" ]]; then
    CACHE_FILE="$(stable_cache_root)/$(cache_key).json"
    if cached="$(read_cache "$CACHE_TTL" "$CACHE_FILE" 2>/dev/null)"; then
        if [[ -n "$JSON_OUT" ]]; then
            printf '%s\n' "$cached" > "$JSON_OUT"
        else
            printf '%s\n' "$cached"
        fi
        exit 0
    fi
fi

collect_latest
collect_tags
select_target
collect_target_tags
verify_target

if [[ "$MODE" == "resolve" ]]; then
    emit_json "$JQ_DIR/registry_resolve_output.jq"
else
    emit_json "$JQ_DIR/registry_check_output.jq"
fi
