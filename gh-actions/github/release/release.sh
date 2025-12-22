#!/usr/bin/env bash

set -e -o pipefail

# Expected environment variables:
# - DEBUG: echo args as executed
# - SHA: the release sha
# - TAG: the release tag
# - TITLE: the release title
# - REPO: the repository
# - FAIL_IF_EXISTS: whether to fail if release exists
# - DRY_RUN: whether this is a dry run
# - NEXT_VERSION: next version to write to version file
# - VERSION: the release version
# - VERSION_FILE: path to version file
# - REOPEN_MESSAGE: commit message for version file update

cleanup() {
    local exit_code=$?
    cat "$TMP_OUTPUT"
    rm -f "$TMP_OUTPUT"
    rm -f "$CMD_OUTPUT"
    exit $exit_code
}

trap cleanup EXIT

RELEASE_ARGS=(
    --target "$SHA"
    --title "$TAG"
    --notes "${TITLE} release ${VERSION}"
    --repo "$REPO"
    "${TAG}")
TMP_OUTPUT="$(mktemp)"
CMD_OUTPUT="$(mktemp)"

if [[ -n "$DEBUG" ]]; then
    gh version >&2
fi

print_cmd() {
    local arg
    for arg in "$@"; do
        if [[ "$arg" =~ [[:space:]] ]]; then
            printf '"%s" ' "$arg"
        else
            printf '%s ' "$arg"
        fi
    done
    echo
}

_run () {
    echo "$ $(print_cmd "$@")" >> "$TMP_OUTPUT"
    if [[ -n "$DEBUG" ]]; then
        echo "$ $(print_cmd "$@")" >&2
    fi
    if [[ "${DRY_RUN}" == "true" && ("$*" =~ "gh release create" || "$*" =~ "git push") ]]; then
        echo "SKIPPED" >> "$TMP_OUTPUT"
        return
    fi
    EXIT_CODE=
    "$@" 2>&1 | tee -a bar >&2 > "$CMD_OUTPUT" || {
        EXIT_CODE="$?"
    }
    if [[ -n "$DEBUG" ]]; then
        cat "$CMD_OUTPUT" >&2
    fi
    cat "$CMD_OUTPUT" >> "$TMP_OUTPUT"
    if [[ -n "$EXIT_CODE" ]]; then
        return "$EXIT_CODE"
    fi
}

if gh release view "$TAG" --repo "$REPO" &>/dev/null; then
    if [[ "${FAIL_IF_EXISTS}" == "true" ]]; then
        echo "::error::Release $TAG already exists, skipping creation" >&2
        exit 1
    fi
    echo "::warning::Release $TAG already exists, skipping creation" >&2
    echo "$ gh release view \"$TAG\" --repo \"$REPO\"" >> "$TMP_OUTPUT"
    echo "Release $TAG already exists, skipping creation" >> "$TMP_OUTPUT"
    exit 0
fi

_run gh release create "${RELEASE_ARGS[@]}"
echo "$ echo ${NEXT_VERSION} > ${VERSION_FILE}" >> "$TMP_OUTPUT"
if [[ -n "$DEBUG" ]]; then
    echo "$ echo ${NEXT_VERSION} > ${VERSION_FILE}" >&2
fi
echo "${NEXT_VERSION}" > "${VERSION_FILE}"
_run git commit "${VERSION_FILE}" -m "${REOPEN_MESSAGE}" --signoff
_run git show
_run git push origin refs/heads/main
