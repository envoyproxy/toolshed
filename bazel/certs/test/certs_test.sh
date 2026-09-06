#!/bin/bash
set -euo pipefail

root="${RUNFILES_DIR:-$0.runfiles}/${TEST_WORKSPACE}/certs/test"
fixture="$root/fixtures"

test -s "$root/ca_cert_info.h"
grep -q '^#pragma once$' "$root/ca_cert_info.h"
grep -q 'TEST_CA_CERT_256_HASH' "$root/ca_cert_info.h"
grep -q 'TEST_CA_CERT_1_HASH' "$root/ca_cert_info.h"
grep -q 'TEST_CA_CERT_SPKI' "$root/ca_cert_info.h"
grep -q 'TEST_CA_CERT_SERIAL.*1234' "$root/ca_cert_info.h"
grep -q 'Jan  1 00:00:00 2030 GMT' "$root/ca_cert_info.h"
grep -q 'Jan  1 00:00:00 2032 GMT' "$root/ca_cert_info.h"
grep -q 'TEST_LEAF_CERT_256_HASH' "$root/leaf_cert_info.h"
grep -q 'TEST_LEAF_CERT_SERIAL' "$root/leaf_cert_info.h"
grep -q 'Jan  1 00:00:00 2030 GMT' "$root/leaf_cert_info.h"
grep -q 'Jan  1 00:00:00 2080 GMT' "$root/long_cert_info.h" || true

while IFS= read -r line; do
    test "${#line}" -le 100
done < "$root/ca_cert_info.h"
grep -q '"' "$root/ca_cert_hash.h"
grep -q '"' "$root/leaf_cert_hash.h"

test ! -e "$root/hidden.pem"
test -s "$root/chain.pem"
test -s "$root/revoked.crl.pem"
grep -q '^-----BEGIN X509 CRL-----$' "$root/revoked.crl.pem"
for p12 in bundle.p12 unencrypted.p12; do
    test "$(od -An -t x1 -N 1 "$root/$p12" | tr -d ' ')" = 30
done

test "$(od -An -t x1 -N 1 "$root/statuses.der" | tr -d ' ')" = 30
test "$(od -An -t x1 "$root/statuses.der" | tr -d ' \n' | grep -o '2b0601050507300101' | head -1)" = 2b0601050507300101
grep -q 'TEST_OCSP_THIS_UPDATE' "$root/ocsp_info.h"
grep -q 'TEST_OCSP_NEXT_UPDATE' "$root/ocsp_info.h"

"${JQ_BIN}" -e '
  .trust_domains["example.org"].sequence_number == 7 and
  .trust_domains["other.example"].sequence_number == 9 and
  all(.trust_domains[] .keys[]; .kty == "RSA" and .e == "AQAB" and
    (all(.x5c[]; test("^[A-Za-z0-9+/]+=*$"))) and
    (.n | test("^[A-Za-z0-9_-]+$")))
' "$root/trust-bundle.json" >/dev/null

test -s "$root/serial_ca.pem"
test -s "$root/serial_leaf.pem"
cmp "$root/serial_ca.pem" "$root/serial_ca_2.pem"
cmp "$root/serial_leaf.pem" "$root/serial_leaf_2.pem"
grep -q '1234' "$root/ca_cert_info.h"
test -s "$fixture/ca_key.pem"
