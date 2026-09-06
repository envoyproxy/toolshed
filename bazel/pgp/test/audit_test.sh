#!/usr/bin/env bash
#
# Audit OpenPGP signing actions.
#
# Asserts that, for the given target patterns:
#
#   1. every action with mnemonic `OpenPGPSign` carries all of the required
#      execution requirements,
#   2. no action in the queried universe has an input that looks like private
#      key material or a passphrase,
#   3. no `OpenPGPSign` action has `HOME`, `GNUPGHOME` or `SSH_AUTH_SOCK` in
#      its environment,
#   4. no `OpenPGPSign` action's argv contains a forbidden string (use
#      `--forbid` to check that a passphrase never reaches a command line).
#
# Usage:
#
#   audit_test.sh [--forbid STRING]... [BAZEL OPTION]... //your/targets/...
#   audit_test.sh [--forbid STRING]... --aquery-json aquery.json
#
# The second form audits a previously captured
# `bazel aquery --output=jsonproto` result, which is how this script is
# exercised in tests.

# jq filters are single-quoted on purpose - `$mnemonic` etc are jq
# variables passed with `--arg`, not shell variables.
# shellcheck disable=SC2016

set -euo pipefail

BAZEL="${BAZEL:-bazel}"
JQ="${JQ_BIN:-jq}"

REQUIRED_EXECUTION_REQUIREMENTS=(
    local
    no-cache
    no-remote
    no-remote-cache
    no-remote-cache-upload
    no-remote-exec)
FORBIDDEN_ENV=(
    GNUPGHOME
    HOME
    SSH_AUTH_SOCK)
FORBIDDEN_INPUTS='(^|/)\.gnupg(/|$)|private-keys-v1\.d|passphrase'
MNEMONIC=OpenPGPSign

AQUERY_JSON=
FORBIDDEN_STRINGS=()
BAZEL_OPTS=()
TARGETS=()

usage () {
    echo "usage: $0 [--forbid STRING]... [--aquery-json FILE]" \
         "[BAZEL OPTION]... [TARGET...]" >&2
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --aquery-json)
            AQUERY_JSON="$2"
            shift 2
            ;;
        --forbid)
            FORBIDDEN_STRINGS+=("$2")
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            # Anything else is passed through to `bazel aquery`, eg
            # `--@envoy_toolshed//pgp:passphrase_path=...`.
            BAZEL_OPTS+=("$1")
            shift
            ;;
        *)
            TARGETS+=("$1")
            shift
            ;;
    esac
done

if [[ -z "$AQUERY_JSON" && ${#TARGETS[@]} -eq 0 ]]; then
    usage
fi

if ! command -v "$JQ" > /dev/null 2>&1; then
    echo "jq not found (set JQ_BIN)" >&2
    exit 1
fi

if [[ -z "$AQUERY_JSON" ]]; then
    AQUERY_JSON="$(mktemp)"
    # shellcheck disable=SC2064
    trap "rm -f \"$AQUERY_JSON\"" EXIT
    "$BAZEL" aquery --output=jsonproto --include_artifacts=true \
             ${BAZEL_OPTS[@]+"${BAZEL_OPTS[@]}"} \
             "${TARGETS[@]}" > "$AQUERY_JSON"
fi

FAILED=0

fail () {
    echo "AUDIT FAILURE: $*" >&2
    FAILED=1
}

jqq () {
    "$JQ" -r "$@" "$AQUERY_JSON"
}

signing_actions="$(jqq --arg mnemonic "$MNEMONIC" \
    '[.actions[]? | select(.mnemonic == $mnemonic)] | length')"

echo "Auditing ${signing_actions} ${MNEMONIC} action(s) in ${AQUERY_JSON}"

# 1. Execution requirements.
for requirement in "${REQUIRED_EXECUTION_REQUIREMENTS[@]}"; do
    missing="$(jqq --arg mnemonic "$MNEMONIC" --arg key "$requirement" '
        [.actions[]?
         | select(.mnemonic == $mnemonic)
         | select([.executionInfo[]?.key] | index($key) | not)
         | .targetId // .mnemonic]
        | join(" ")')"
    if [[ -n "$missing" ]]; then
        fail "${MNEMONIC} action(s) missing execution requirement" \
             "\`${requirement}\`: ${missing}"
    fi
done

# 2. Suspicious inputs anywhere in the queried universe.
suspicious="$(jqq --arg re "$FORBIDDEN_INPUTS" '
    [.artifacts[]?
     | .execPath // empty
     | select(test($re; "i"))]
    | unique | join(" ")')"
if [[ -n "$suspicious" ]]; then
    fail "action inputs look like key material or passphrases: ${suspicious}"
fi

# 3. Forbidden environment variables.
for name in "${FORBIDDEN_ENV[@]}"; do
    leaked="$(jqq --arg mnemonic "$MNEMONIC" --arg key "$name" '
        [.actions[]?
         | select(.mnemonic == $mnemonic)
         | select([.environmentVariables[]?.key] | index($key))
         | .targetId // .mnemonic]
        | join(" ")')"
    if [[ -n "$leaked" ]]; then
        fail "${MNEMONIC} action(s) leak \`${name}\` into the environment:" \
             "${leaked}"
    fi
done

# 4. Forbidden strings (eg the passphrase) in argv.
for forbidden in ${FORBIDDEN_STRINGS[@]+"${FORBIDDEN_STRINGS[@]}"}; do
    found="$(jqq --arg mnemonic "$MNEMONIC" --arg forbidden "$forbidden" '
        [.actions[]?
         | select(.mnemonic == $mnemonic)
         | select([.arguments[]? | select(contains($forbidden))] | length > 0)
         | .targetId // .mnemonic]
        | join(" ")')"
    if [[ -n "$found" ]]; then
        fail "${MNEMONIC} action(s) pass a forbidden string on the command" \
             "line: ${found}"
    fi
done

if [[ "$FAILED" -ne 0 ]]; then
    echo "OpenPGP signing audit FAILED" >&2
    exit 1
fi

echo "OpenPGP signing audit passed"
