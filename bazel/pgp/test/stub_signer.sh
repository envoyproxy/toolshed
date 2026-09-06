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
        --armor|--require-encrypted-key)
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if [[ -z "$MODE" || -z "$KEY" || -z "$PASSPHRASE_FILE" || -z "$OUT" ]]; then
    echo "stub signer: incomplete arguments" >&2
    exit 2
fi

echo "STUB SIGNATURE (${MODE})" > "$OUT"
