#!/usr/bin/env bash

set -e -o pipefail


VERSION_DIR="${GITHUB_WORKSPACE}/${MODULES_ROOT}/modules/${MODULE}/${MODULE_VERSION}"

curl -sLo upstream.tar.gz "$SOURCE_URL"
echo "integrity sha256-$(openssl dgst -sha256 -binary < upstream.tar.gz | base64)"

if [[ -d "${VERSION_DIR}/overlay" ]]; then
    find "${VERSION_DIR}/overlay" -type f | sort | while read -r file; do
        relpath="${file#"${VERSION_DIR}"/overlay/}"
        checksum="sha256-$(openssl dgst -sha256 -binary < "$file" | base64)"
        echo "overlay:$relpath $checksum"
    done
fi

if [[ -d "${VERSION_DIR}/patches" ]]; then
    find "${VERSION_DIR}/patches" -type f | sort | while read -r file; do
        relpath="${file#"${VERSION_DIR}"/patches/}"
        checksum="sha256-$(openssl dgst -sha256 -binary < "$file" | base64)"
        echo "patches:$relpath $checksum"
    done
fi
