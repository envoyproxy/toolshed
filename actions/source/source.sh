#!/usr/bin/env bash

set -e -o pipefail

VERSION=$(tr -d '\n' < "$VERSION_FILE")
TARBALL_NAME="${OUTPUT_NAME//\{version\}/$VERSION}"

cd "$WORKING_DIRECTORY"

TAR_CMD=(tar)
read -ra EXCLUDE_ARGS <<< "$EXCLUDES"
TAR_CMD+=("${EXCLUDE_ARGS[@]}")
if [[ -n "$TRANSFORM_ARG" ]]; then
    TRANSFORM_EXPANDED="${TRANSFORM_ARG//\{version\}/$VERSION}"
    TAR_CMD+=("$TRANSFORM_EXPANDED")
fi
TAR_CMD+=(-czf "$TARBALL_NAME" "$SOURCE_PATH")

if [[ -n "$DEBUG" ]]; then
    echo "VERSION: ${VERSION}" >&2
    echo "TARBALL_NAME: ${TARBALL_NAME}" >&2
    echo "EXCLUDES: ${EXCLUDES}" >&2
    echo "TRANSFORM: ${TRANSFORM_ARG}" >&2
    echo "RUN: ${TAR_CMD[*]}" >&2
fi
"${TAR_CMD[@]}"

echo "tarball=${TARBALL_NAME}"
echo "version=${VERSION}"
