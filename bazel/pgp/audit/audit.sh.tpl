#!/usr/bin/env bash
set -euo pipefail

resolve_runfile() {
    local path="$1"
    if [[ -n "${RUNFILES_DIR:-}" && -e "${RUNFILES_DIR}/${path}" ]]; then
        printf '%s\n' "${RUNFILES_DIR}/${path}"
        return 0
    fi
    if [[ -e "$0.runfiles/${path}" ]]; then
        printf '%s\n' "$0.runfiles/${path}"
        return 0
    fi
    printf 'runfile not found: %s\n' "${path}" >&2
    return 1
}

jq_bin="$(resolve_runfile @JQ@)"
filter="$(resolve_runfile @FILTER@)"
lib_dir="$(resolve_runfile @LIB_DIR@)"
mnemonic=@MNEMONIC@
required_exec_reqs=@REQUIRED_EXEC_REQS@
forbidden_env=@FORBIDDEN_ENV@
forbidden_inputs_re=@FORBIDDEN_INPUTS_RE@
forbidden_strings=()
aquery_json=
bazel_opts=()
targets=()

usage() {
    cat >&2 <<'USAGE'
usage: audit [--forbid STRING]... [--aquery-json FILE] [BAZEL OPTION]... [TARGET...]

With --aquery-json, audit captured `bazel aquery --output=jsonproto` JSON.
Without --aquery-json, run `bazel aquery` for the supplied target patterns first.
USAGE
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --aquery-json)
            [[ $# -ge 2 ]] || usage
            aquery_json="$2"
            shift 2
            ;;
        --forbid)
            [[ $# -ge 2 ]] || usage
            forbidden_strings+=("$2")
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            bazel_opts+=("$1")
            shift
            ;;
        *)
            targets+=("$1")
            shift
            ;;
    esac
done

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

if [[ -z "$aquery_json" ]]; then
    [[ ${#targets[@]} -gt 0 ]] || usage
    aquery_json="$tmp/aquery.json"
    bazel aquery --output=jsonproto --include_artifacts=true \
        ${bazel_opts[@]+"${bazel_opts[@]}"} \
        "${targets[@]}" > "$aquery_json"
fi

# shellcheck disable=SC2016
forbidden_strings_json="$("$jq_bin" -n '$ARGS.positional' --args "${forbidden_strings[@]}")"
report="$tmp/report.json"
"$jq_bin" \
    -L "$lib_dir" \
    -f "$filter" \
    --arg mnemonic "$mnemonic" \
    --argjson required_exec_reqs "$required_exec_reqs" \
    --argjson forbidden_env "$forbidden_env" \
    --arg forbidden_inputs_re "$forbidden_inputs_re" \
    --argjson forbidden_strings "$forbidden_strings_json" \
    "$aquery_json" > "$report"
cat "$report"
"$jq_bin" -e '(.failures | length) == 0' "$report" > /dev/null
