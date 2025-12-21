#!/usr/bin/env bash

set -e -o pipefail

# Expected environment variables:
# - RELEASE_ARGS: arguments for gh release create
# - TAG: the release tag
# - REPO: the repository
# - FAIL_IF_EXISTS: whether to fail if release exists
# - DRY_RUN: whether this is a dry run
# - NEXT_VERSION: next version to write to version file
# - VERSION_FILE: path to version file
# - REOPEN_MESSAGE: commit message for version file update

read -ra RELEASE_ARGS_ARR <<< "$RELEASE_ARGS"


if gh release view "$TAG" --repo "$REPO" &>/dev/null; then
    if [[ "${FAIL_IF_EXISTS}" == "true" ]]; then
        echo "::error::Release $TAG already exists, skipping creation" >&2
        exit 1
    fi
    echo "::warning::Release $TAG already exists, skipping creation" >&2
    OUTPUT=(
        "$ gh release view \"$TAG\" --repo \"$REPO\""
        "Release $TAG already exists, skipping creation")
    _OUTPUT=$(printf '%s\n' "${OUTPUT[@]}")
    echo "${_OUTPUT}"
    exit 0
fi
OUTPUT=("$ gh release create ${RELEASE_ARGS[*]}")
if [[ "${DRY_RUN}" == "true" ]]; then
    OUTPUT+=("SKIPPED")
else
    OUTPUT+=("$(gh release create "${RELEASE_ARGS_ARR[@]}")")
fi
echo "${NEXT_VERSION}" > "${VERSION_FILE}"
OUTPUT+=("$ git commit ${VERSION_FILE} -m \"${REOPEN_MESSAGE}\" --signoff")
OUTPUT+=("$(git commit "${VERSION_FILE}" -m "${REOPEN_MESSAGE}" --signoff)")
OUTPUT+=("$ git push origin refs/heads/main")
if [[ "${DRY_RUN}" == "true" ]]; then
    OUTPUT+=("SKIPPED")
else
    OUTPUT+=("$(git push origin refs/heads/main)")
fi
_OUTPUT=$(printf '%s\n' "${OUTPUT[@]}")
echo "${_OUTPUT}"
