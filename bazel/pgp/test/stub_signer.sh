#!/usr/bin/env bash
#
# Stub signer used by the analysis tests.
#
# It implements the argument contract of the real signer but performs no
# cryptography - the analysis tests only need a registered toolchain.

set -euo pipefail

MODE=
KEY=
PASSPHRASE_FILE=
OUT=
INPUTS=()

usage () {
    echo "usage: $0 --mode MODE --key KEY [--key-sha256 HEX]" \
         "--passphrase-file PATH --out OUT [--armor]" \
         "[--require-encrypted-key] INPUT" >&2
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
        --key-sha256)
            # Accepted for contract parity; the stub does no verification.
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
        --armor|--require-encrypted-key)
            shift
            ;;
        -*)
            echo "stub signer: unknown option: $1" >&2
            usage
            ;;
        *)
            INPUTS+=("$1")
            shift
            ;;
    esac
done

if [[ -z "$MODE" || -z "$KEY" || -z "$PASSPHRASE_FILE" || -z "$OUT" ]]; then
    echo "stub signer: incomplete arguments" >&2
    usage
fi

if [[ ${#INPUTS[@]} -ne 1 ]]; then
    echo "stub signer: expected exactly one input, got ${#INPUTS[@]}" >&2
    usage
fi

echo "STUB SIGNATURE (${MODE})" > "$OUT"
