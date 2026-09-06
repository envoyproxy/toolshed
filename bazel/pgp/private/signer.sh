#!/usr/bin/env bash
#
# Thin wrapper translating the toolshed signer CLI contract to Sequoia PGP
# (`sq`) invocations.
#
#   signer --mode {detached|cleartext|inline} \
#          --key <encrypted-secret-key-file> \
#          --passphrase-file <abs-path> \
#          --require-encrypted-key \
#          --out <output-file> \
#          [--armor] \
#          <input>...
#
# The wrapper deliberately never consults `HOME`, `GNUPGHOME`, a gpg-agent
# socket, or any on-disk keyring/cert store - `sq` is invoked with its own
# state directories disabled. It operates purely on the key file, the
# passphrase file and the declared inputs.

set -euo pipefail

# Baked in at build time by `sq_signer`. `SQ` can be set when running this
# script outside of Bazel (eg the integration test).
SQ="${SQ:-@SQ@}"

MODE=
KEY=
PASSPHRASE_FILE=
OUT=
ARMOR=0
REQUIRE_ENCRYPTED_KEY=0
PASSPHRASE_COPY=
INPUTS=()

usage () {
    echo "usage: $0 --mode {detached|cleartext|inline} --key KEY" \
         "--passphrase-file PATH --out OUT [--armor]" \
         "[--require-encrypted-key] INPUT..." >&2
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --key)
            KEY="$2"
            shift 2
            ;;
        --passphrase-file)
            PASSPHRASE_FILE="$2"
            shift 2
            ;;
        --out)
            OUT="$2"
            shift 2
            ;;
        --armor)
            ARMOR=1
            shift
            ;;
        --require-encrypted-key)
            REQUIRE_ENCRYPTED_KEY=1
            shift
            ;;
        --)
            shift
            INPUTS+=("$@")
            break
            ;;
        -*)
            echo "unknown option: $1" >&2
            usage
            ;;
        *)
            INPUTS+=("$1")
            shift
            ;;
    esac
done

if [[ -z "$MODE" || -z "$KEY" || -z "$PASSPHRASE_FILE" || -z "$OUT" ]]; then
    usage
fi

if [[ ${#INPUTS[@]} -eq 0 ]]; then
    echo "no input files given" >&2
    usage
fi

# The placeholder is split so that `sq_signer` template expansion does not
# rewrite this check too.
if [[ "$SQ" == "@""SQ""@" ]]; then
    echo "no \`sq\` binary configured (SQ is unset and the wrapper was not" \
         "expanded by \`sq_signer\`)" >&2
    exit 1
fi

if [[ ${#INPUTS[@]} -gt 1 ]]; then
    echo "the signer accepts a single input file, got ${#INPUTS[@]}" >&2
    exit 2
fi

if [[ ! -f "$KEY" ]]; then
    echo "key file not found: $KEY" >&2
    exit 1
fi

if [[ ! -f "$PASSPHRASE_FILE" ]]; then
    echo "passphrase file not found: ${PASSPHRASE_FILE}" >&2
    echo "the passphrase file must exist on the host running the build," \
         "see --@envoy_toolshed//pgp:passphrase_path" >&2
    exit 1
fi

# `sq` state directories are disabled unconditionally: no home, no cert store,
# no key store, and no prompting. Nothing outside the arguments is consulted.
sq () {
    "$SQ" \
        --batch \
        --overwrite \
        --home none \
        --cert-store none \
        --key-store none \
        "$@"
}

# Fail hard unless *every* secret key packet in the key file is protected.
#
# `sq inspect` prints `Secret key: Encrypted` or `Secret key: Unencrypted` for
# each secret key packet. A key with no secret key packets at all cannot sign,
# and is rejected here rather than producing a confusing error later.
require_encrypted_key () {
    local inspected secret unencrypted
    if ! inspected="$(sq inspect "$KEY" 2>&1)"; then
        echo "unable to inspect key: $KEY" >&2
        echo "$inspected" >&2
        exit 1
    fi
    secret="$(printf '%s\n' "$inspected" | grep -c 'Secret key: ' || true)"
    unencrypted="$(
        printf '%s\n' "$inspected" | grep -c 'Secret key: Unencrypted' || true)"
    if [[ "$secret" -eq 0 ]]; then
        echo "no secret key material found in ${KEY}" >&2
        exit 1
    fi
    if [[ "$unencrypted" -ne 0 ]]; then
        echo "REFUSING TO SIGN: ${KEY} contains unprotected secret key" \
             "material." >&2
        echo "The key given to the signing rules must be" \
             "passphrase-encrypted, so that the only key material Bazel can" \
             "hash, cache or upload is ciphertext." >&2
        exit 1
    fi
}

# `sq` uses the entire contents of the password file, including any trailing
# newline, whereas `gpg --passphrase-file` strips it. Normalize on the `gpg`
# behaviour by stripping trailing newlines into a private copy.
#
# The copy lives in the action's (sandboxed, per-action) temporary directory,
# is created with mode 600, and is removed on exit.
normalize_passphrase_file () {
    local tmpdir
    tmpdir="$(mktemp -d)"
    # shellcheck disable=SC2064
    trap "rm -rf \"$tmpdir\"" EXIT
    PASSPHRASE_COPY="${tmpdir}/passphrase"
    (
        umask 077
        printf %s "$(cat "$PASSPHRASE_FILE")" > "$PASSPHRASE_COPY"
    )
}

if [[ "$REQUIRE_ENCRYPTED_KEY" -eq 1 ]]; then
    require_encrypted_key
fi

normalize_passphrase_file

args=(
    --password-file "$PASSPHRASE_COPY"
    sign
    --signer-file "$KEY")

case "$MODE" in
    detached)
        args+=(--signature-file "$OUT")
        ;;
    cleartext)
        args+=(--cleartext --output "$OUT")
        ;;
    inline)
        args+=(--message --output "$OUT")
        ;;
    *)
        echo "unknown mode: $MODE" >&2
        usage
        ;;
esac

# Cleartext signatures are armored by definition.
if [[ "$MODE" != "cleartext" && "$ARMOR" -eq 0 ]]; then
    args+=(--binary)
fi

sq "${args[@]}" "${INPUTS[0]}"
