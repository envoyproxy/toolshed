#!/usr/bin/env bash
#
# Integration test for the signer CLI contract.
#
# Generates a passphrase-encrypted key with `sq` at test time (no key material
# is ever committed), signs in each mode, verifies the signatures, and asserts
# that the signer refuses to use an unencrypted key.
#
# Skipped if no `sq` is available - the default toolchain binary is not
# fetched by default (see //pgp:extensions.bzl).

set -euo pipefail

SQ="${SQ:-}"
if [[ -z "$SQ" ]]; then
    SQ="$(command -v sq || true)"
fi

if [[ -z "$SQ" ]]; then
    echo "SKIP: no \`sq\` binary found (set SQ to run this test)"
    exit 0
fi

SIGNER="$(dirname "$0")/../private/signer.sh"
if [[ ! -f "$SIGNER" ]]; then
    SIGNER="pgp/private/signer.sh"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASSPHRASE_FILE="${TMP}/passphrase"
KEY="${TMP}/key.pgp"
UNENCRYPTED_KEY="${TMP}/unencrypted-key.pgp"
DATA="${TMP}/data.txt"

sq () {
    "$SQ" --batch --home none --cert-store none --key-store none "$@"
}

signer () {
    SQ="$SQ" bash "$SIGNER" "$@"
}

printf %s "test-passphrase-$$" > "$PASSPHRASE_FILE"
chmod 600 "$PASSPHRASE_FILE"
echo "some data" > "$DATA"

sq key generate --own-key --without-password --no-userids \
   --output "$UNENCRYPTED_KEY"
sq key generate --own-key --new-password-file "$PASSPHRASE_FILE" \
   --no-userids --output "$KEY"
failed=0

check () {
    local msg="$1"
    shift
    if "$@"; then
        echo "ok: ${msg}"
    else
        echo "FAIL: ${msg}" >&2
        failed=1
    fi
}

check_fails () {
    local msg="$1"
    shift
    if "$@" > "${TMP}/output" 2>&1; then
        echo "FAIL: ${msg}" >&2
        failed=1
    else
        echo "ok: ${msg}"
    fi
}

# Detached signature.
check "detached signature created" \
      signer --mode detached --key "$KEY" \
      --passphrase-file "$PASSPHRASE_FILE" --require-encrypted-key \
      --armor --out "${TMP}/data.txt.asc" "$DATA"
check "detached signature verifies" \
      sq verify --signature-file "${TMP}/data.txt.asc" \
      --signer-file "$KEY" "$DATA"

# Cleartext signature.
check "cleartext signature created" \
      signer --mode cleartext --key "$KEY" \
      --passphrase-file "$PASSPHRASE_FILE" --require-encrypted-key \
      --out "${TMP}/data.txt.cleartext" "$DATA"
check "cleartext signature is a cleartext signed message" \
      grep -q -- "-----BEGIN PGP SIGNED MESSAGE-----" \
      "${TMP}/data.txt.cleartext"
check "cleartext signature verifies" \
      sq verify --cleartext --signer-file "$KEY" \
      "${TMP}/data.txt.cleartext"

# Inline signature.
check "inline signature created" \
      signer --mode inline --key "$KEY" \
      --passphrase-file "$PASSPHRASE_FILE" --require-encrypted-key \
      --armor --out "${TMP}/data.txt.inline" "$DATA"
check "inline signature verifies" \
      sq verify --message --signer-file "$KEY" \
      --output /dev/null "${TMP}/data.txt.inline"

# Unencrypted keys must be rejected.
check_fails "unencrypted key is rejected" \
            signer --mode detached --key "$UNENCRYPTED_KEY" \
            --passphrase-file "$PASSPHRASE_FILE" --require-encrypted-key \
            --armor --out "${TMP}/rejected.asc" "$DATA"
check "rejection is explicit" \
      grep -q "REFUSING TO SIGN" "${TMP}/output"
check "no output was written for a rejected key" \
      test ! -e "${TMP}/rejected.asc"

if [[ "$failed" -ne 0 ]]; then
    exit 1
fi

echo "signer integration test passed"
