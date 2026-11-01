#!/usr/bin/env bash

set -e -o pipefail


MODULE_BAZEL="rules_jq/MODULE.bazel"

# `rules_jq` is versioned independently of toolshed, so only its own
# `module()` version follows rules_jq/VERSION.txt.
MODULE_VERSION_SED="/^module(/,/^)/s/version = \"[^\"]*\"/version = \"${NEXT_VERSION}\"/"

COMMANDS=(
    "sed -i '${MODULE_VERSION_SED}' ${MODULE_BAZEL}"
)

{
    for cmd in "${COMMANDS[@]}"; do
        echo "\$ ${cmd}"
    done
} >> "$TMP_OUTPUT"
if [[ -n "$DEBUG" ]]; then
    for cmd in "${COMMANDS[@]}"; do
        echo "\$ ${cmd}" >&2
    done
fi

sed -i "${MODULE_VERSION_SED}" "${MODULE_BAZEL}"

echo "${MODULE_BAZEL}"
