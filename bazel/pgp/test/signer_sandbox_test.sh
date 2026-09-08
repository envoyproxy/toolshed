#!/usr/bin/env bash
#
# In-graph regression test for the built signer wrapper.
#
# Unlike `signer_test.sh`, which runs the raw script, this drives the
# `expand_template` output of `//pgp:sq_signer` inside the Bazel test sandbox -
# the environment that exposed the passphrase fd-lifetime bug, where the
# `/dev/fd/N` created by a process substitution in an array assignment was
# already closed by the time `sq` ran:
#
#   Error: Reading /dev/fd/63
#   because: No such file or directory (os error 2)
#
# Everything (key, passphrase, inputs, outputs) lives in `$TEST_TMPDIR`.

set -euo pipefail

abspath () {
    if [[ "$1" == /* ]]; then
        echo "$1"
    else
        echo "${PWD}/$1"
    fi
}

SQ="$(abspath "${SQ:?SQ must point at a \`sq\` binary}")"
SIGNER="$(abspath "${SQ_SIGNER:?SQ_SIGNER must point at the built sq_signer}")"

if [[ ! -x "$SQ" ]]; then
    echo "no usable \`sq\` binary: ${SQ}" >&2
    exit 1
fi

if [[ ! -x "$SIGNER" ]]; then
    echo "no usable signer: ${SIGNER}" >&2
    exit 1
fi

TMP="${TEST_TMPDIR:-$(mktemp -d)}"

PASSPHRASE_FILE="${TMP}/passphrase"
KEY="${TMP}/key.pgp"
DATA="${TMP}/data.txt"

sq () {
    "$SQ" --batch --home none --cert-store none --key-store none "$@"
}

# `SQ` is exported so the wrapper uses the hermetic `sq` from runfiles rather
# than the exec-configuration path baked in at analysis time, which does not
# resolve inside a test's runfiles tree.
signer () {
    SQ="$SQ" "$SIGNER" "$@"
}

# A trailing newline in the passphrase file is what the wrapper strips via the
# process substitution, so generate one that has it.
printf '%s\n' "test-passphrase-$$" > "$PASSPHRASE_FILE"
chmod 600 "$PASSPHRASE_FILE"
echo "some data" > "$DATA"

sq key generate --own-key --new-password-file "$PASSPHRASE_FILE" \
   --no-userids --rev-cert "${KEY}.rev" --output "$KEY" > /dev/null

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

check "detached signature created by the built signer" \
      signer --mode detached --key "$KEY" \
      --passphrase-file "$PASSPHRASE_FILE" --require-encrypted-key \
      --armor --out "${TMP}/data.txt.asc" "$DATA"
check "detached signature verifies" \
      sq verify --signature-file "${TMP}/data.txt.asc" \
      --signer-file "$KEY" "$DATA"

check "cleartext signature created by the built signer" \
      signer --mode cleartext --key "$KEY" \
      --passphrase-file "$PASSPHRASE_FILE" --require-encrypted-key \
      --out "${TMP}/data.txt.cleartext" "$DATA"
check "cleartext signature verifies" \
      sq verify --cleartext --signer-file "$KEY" \
      "${TMP}/data.txt.cleartext"

if [[ "$failed" -ne 0 ]]; then
    exit 1
fi

echo "sandboxed signer test passed"
