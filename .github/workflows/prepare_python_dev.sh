#!/usr/bin/env bash

set -e -o pipefail


for version_file in py/*/VERSION; do
    current="$(tr -d '[:space:]' < "${version_file}")"
    if [[ "${current}" == *-dev ]]; then
        continue
    fi
    if [[ ! "${current}" =~ ^([0-9]+\.[0-9]+\.)([0-9]+)$ ]]; then
        echo "Failed to parse version '${current}' in ${version_file}" >&2
        exit 1
    fi
    patch="${BASH_REMATCH[2]}"
    next="${BASH_REMATCH[1]}$((patch + 1))-dev"
    echo "\$ echo ${next} > ${version_file}" >> "$TMP_OUTPUT"
    if [[ -n "$DEBUG" ]]; then
        echo "\$ echo ${next} > ${version_file}" >&2
    fi
    echo "${next}" > "${version_file}"
    echo "${version_file}"
done
