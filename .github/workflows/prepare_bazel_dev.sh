#!/usr/bin/env bash

set -e -o pipefail


MODULE_BAZEL="bazel/MODULE.bazel"
JQ_MODULE_BAZEL="jq/MODULE.bazel"

# `jq/` is versioned and released together with `envoy_toolshed` (see
# `jq/README.md`), so its own `module()` version and the `envoy_toolshed_jq`
# `bazel_dep` pin in `bazel/MODULE.bazel` are bumped in lockstep here.
MODULE_VERSION_SED="/^module(/,/^)/s/version = \"[^\"]*\"/version = \"${NEXT_VERSION}\"/"
JQ_DEP_VERSION_SED="/name = \"envoy_toolshed_jq\"/s/version = \"[^\"]*\"/version = \"${NEXT_VERSION}\"/"

COMMANDS=(
    "sed -i '${MODULE_VERSION_SED}' ${MODULE_BAZEL}"
    "sed -i '${MODULE_VERSION_SED}' ${JQ_MODULE_BAZEL}"
    "sed -i '${JQ_DEP_VERSION_SED}' ${MODULE_BAZEL}"
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
sed -i "${MODULE_VERSION_SED}" "${JQ_MODULE_BAZEL}"
sed -i "${JQ_DEP_VERSION_SED}" "${MODULE_BAZEL}"

echo "${MODULE_BAZEL}"
echo "${JQ_MODULE_BAZEL}"
