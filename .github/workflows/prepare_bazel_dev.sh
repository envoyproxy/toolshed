#!/usr/bin/env bash

set -e -o pipefail


MODULE_BAZEL="bazel/MODULE.bazel"
if grep -q -- '--noenable_bzlmod' bazel/.bazelrc; then
    echo "bzlmod disabled; skipping ${MODULE_BAZEL} version bump" >> "$TMP_OUTPUT"
    if [[ -n "$DEBUG" ]]; then
        echo "bzlmod disabled; skipping ${MODULE_BAZEL} version bump" >&2
    fi
    exit 0
fi
echo "\$ sed -i '/^module(/,/^)/s/version = \\\"[^\\\"]*\\\"/version = \\\"${NEXT_VERSION}\\\"/' ${MODULE_BAZEL}" >> "$TMP_OUTPUT"
if [[ -n "$DEBUG" ]]; then
    echo "\$ sed -i '/^module(/,/^)/s/version = \\\"[^\\\"]*\\\"/version = \\\"${NEXT_VERSION}\\\"/' ${MODULE_BAZEL}" >&2
fi
sed -i "/^module(/,/^)/s/version = \"[^\"]*\"/version = \"${NEXT_VERSION}\"/" "${MODULE_BAZEL}"
echo "${MODULE_BAZEL}"
