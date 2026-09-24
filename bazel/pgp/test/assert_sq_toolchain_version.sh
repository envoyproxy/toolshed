#!/bin/bash
set -euo pipefail

: "${SQ:?SQ must be set}"
: "${SQ_VERSION:?SQ_VERSION must be set}"
: "${REPO_NAME_FILE:?REPO_NAME_FILE must be set}"

repo_name=$(tr -d '\n' <"$REPO_NAME_FILE")

# `sq version` may emit its version banner on stderr in some environments, so
# validate the first line of the combined output instead of stdout alone.
if ! version_out="$("$SQ" version 2>&1)"; then
    echo "'$SQ version' failed:" >&2
    echo "$version_out" >&2
    exit 1
fi
version="${version_out%%$'\n'*}"
if [[ "$version" != "sq $SQ_VERSION" ]]; then
    echo "unexpected sq version line: '$version' (expected 'sq $SQ_VERSION')" >&2
    echo "full output:" >&2
    echo "$version_out" >&2
    exit 1
fi

if ! echo "$repo_name" | grep -Eq '^[A-Za-z0-9_+.-]*$'; then
    echo "unexpected repo name: '$repo_name'" >&2
    exit 1
fi

if [[ "${EXPECT_SOURCE_ONLY:-0}" == "1" ]]; then
    if [[ "$repo_name" == *sq_toolchains* ]]; then
        echo "expected source toolchain, got prebuilt repo '$repo_name'" >&2
        exit 1
    fi
else
    if [[ "$repo_name" != *sq_toolchains* ]]; then
        echo "expected prebuilt toolchain from @sq_toolchains, got repo '$repo_name'" >&2
        exit 1
    fi
fi

echo "PASS: sq toolchain version checks passed ($repo_name)"
