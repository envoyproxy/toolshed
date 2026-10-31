#!/usr/bin/env bash
# Checks the ispell `-a` pipe protocol with an empty environment (no host config or HOME).
set -euo pipefail

hunspell="$1"
dict="$2"
personal="${TEST_TMPDIR:-$(mktemp -d)}/personal.dic"
printf 'envoyproxy\n' > "$personal"

output="$(printf 'hello\nhelo\nenvoyproxy\nrunning\n' \
    | env - "$hunspell" -a -i utf-8 -d "$dict" -p "$personal")"
mapfile -t lines <<< "$output"

fail() {
    echo "FAIL: $1" >&2
    printf '%s\n' "$output" >&2
    exit 1
}

[[ "${lines[0]}" == "@(#) International Ispell"* ]] || fail "missing ispell banner"
# Each input line yields one result per word, then a blank line.
[[ "${lines[1]}" == "*" ]] || fail "'hello' should be correct"
[[ "${lines[3]}" == "& helo "* ]] || fail "'helo' should be misspelled with suggestions"
[[ "${lines[3]}" == *"hello"* ]] || fail "'helo' should suggest 'hello'"
[[ "${lines[5]}" == "*" ]] || fail "'envoyproxy' should be accepted from the personal dictionary"
[[ "${lines[7]}" == "*" || "${lines[7]}" == "+ "* ]] || fail "'running' should be correct"
echo "PASS"
