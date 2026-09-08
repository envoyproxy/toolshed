#!/usr/bin/env bash
set -euo pipefail

src="$1"
out="$2"

if ! grep -Fq -- '-----BEGIN PGP PUBLIC KEY BLOCK-----' "$src" \
    || ! grep -Fq -- '-----END PGP PUBLIC KEY BLOCK-----' "$src"; then
    echo "refusing non-public OpenPGP key: missing public key block" >&2
    exit 1
fi
if grep -Fq -- 'PRIVATE KEY' "$src"; then
    echo "refusing OpenPGP key containing PRIVATE KEY material" >&2
    exit 1
fi
if [[ "$(grep -Fc -- '-----BEGIN PGP' "$src")" -ne 1 ]]; then
    echo "refusing OpenPGP key containing multiple PGP blocks" >&2
    exit 1
fi
cp "$src" "$out"
