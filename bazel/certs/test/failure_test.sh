#!/bin/bash
set -euo pipefail

gen="$1"
fixture="$(dirname "$2")"
tmp="${TEST_TMPDIR}/cert-failures"
mkdir -p "$tmp"

expect_failure() {
    local name="$1" needle="$2" spec="$3"
    mkdir -p "$tmp/$name"
    if "$gen" --spec "$fixture/$spec" --in-dir "$fixture" --out-dir "$tmp/$name" --year 2030 >"$tmp/$name.out" 2>&1; then
        echo "$name unexpectedly succeeded" >&2
        exit 1
    fi
    grep -Fq "$needle" "$tmp/$name.out"
}

if "$gen" --in-dir "$fixture" --out-dir "$tmp/missing" --year 2030 >"$tmp/missing.out" 2>&1; then
    exit 1
fi
grep -Fq -- "--spec is required" "$tmp/missing.out"

for bad_year in abc 1969; do
    if "$gen" --spec "$fixture/certs.spec" --in-dir "$fixture" --out-dir "$tmp/year-$bad_year" --year "$bad_year" >"$tmp/year-$bad_year.out" 2>&1; then
        exit 1
    fi
    grep -Fq "year" "$tmp/year-$bad_year.out"
done

expect_failure unknown-kind "unknown spec section kind" unknown_kind.spec
expect_failure missing-key "missing required key 'key'" missing_key.spec
expect_failure unknown-fixture "unable to open key" unknown_fixture.spec
expect_failure bad-validity "unknown validity mode" bad_validity.spec
expect_failure bad-ocsp "unknown OCSP certificate status" bad_ocsp.spec
expect_failure ocsp-count "one 'issuer' per 'cert'" ocsp_count.spec
expect_failure bad-domain "malformed trust domain entry" bad_domain.spec
expect_failure outside "value outside section" outside.spec
expect_failure unterminated "unterminated section header" unterminated.spec
expect_failure no-equals "expected 'key = value'" no_equals.spec
