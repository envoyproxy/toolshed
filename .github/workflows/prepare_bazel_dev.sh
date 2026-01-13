#!/usr/bin/env bash

set -e -o pipefail

MODULE_BAZEL="bazel/MODULE.bazel"
echo "\$ sed -i '/^module(/,/^)/s/version = \\\"[^\\\"]*\\\"/version = \\\"${NEXT_VERSION}\\\"/' ${MODULE_BAZEL}" >> "$TMP_OUTPUT"
if [[ -n "$DEBUG" ]]; then
    echo "\$ sed -i '/^module(/,/^)/s/version = \\\"[^\\\"]*\\\"/version = \\\"${NEXT_VERSION}\\\"/' ${MODULE_BAZEL}" >&2
fi
if [[ "${DRY_RUN}" != "true" ]]; then
    sed -i "/^module(/,/^)/s/version = \"[^\"]*\"/version = \"${NEXT_VERSION}\"/" "${MODULE_BAZEL}"
fi
echo "${MODULE_BAZEL}"
