#!/usr/bin/env bash
set -euo pipefail

CHECKER="${CHECKER:?}"
TMP="${TEST_TMPDIR:?}"

expect_pass () {
    local name="$1"
    shift
    if ! "$CHECKER" "$TMP/${name}.checked" "$@"; then
        echo "FAIL: ${name}: checker rejected clean reports" >&2
        exit 1
    fi
    test -f "$TMP/${name}.checked"
}

expect_fail () {
    local name="$1"
    shift
    if "$CHECKER" "$TMP/${name}.checked" "$@" 2> "$TMP/${name}.stderr"; then
        echo "FAIL: ${name}: checker accepted a failing report" >&2
        exit 1
    fi
    test ! -e "$TMP/${name}.checked"
}

: > "$TMP/empty.yaml"

cat > "$TMP/clean.yaml" <<'YAML'
---
MainSourceFile: clean.cc
Diagnostics: []
...
YAML

cat > "$TMP/diagnostic.yaml" <<'YAML'
---
MainSourceFile: violation.cc
Diagnostics:
  - DiagnosticName: misc-unused-using-decls
    DiagnosticMessage:
      Message: using decl 'string' is unused
...
YAML

cat > "$TMP/malformed.yaml" <<'YAML'
---
MainSourceFile: malformed.cc
...
YAML

expect_pass no_reports
expect_pass empty "$TMP/empty.yaml"
expect_pass clean "$TMP/clean.yaml"
expect_pass mixed_clean "$TMP/empty.yaml" "$TMP/clean.yaml"
expect_fail diagnostic "$TMP/diagnostic.yaml"
expect_fail diagnostic_among_clean "$TMP/empty.yaml" "$TMP/diagnostic.yaml" "$TMP/clean.yaml"
expect_fail malformed "$TMP/malformed.yaml"
grep -q "misc-unused-using-decls" "$TMP/diagnostic.stderr"

echo "PASS"
