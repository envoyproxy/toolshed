#!/bin/bash -e

set -o pipefail

JQ="$1"
UPDATE_TOOL="$2"
VERSION_FILE="$3"
DEP_DATA="$4"
DEP="$5"
VERSION="$6"

if [[ -z "$DEP" || -z "$VERSION" ]]; then
    echo "You need to supply dependency and sha to update"
    exit 1
fi

pushd "${BUILD_WORKSPACE_DIRECTORY}" &> /dev/null
VERSION_FILE="$(realpath "${VERSION_FILE}")"
popd &> /dev/null
EXISTING_VERSION="$("${JQ}" -r ".${DEP}.version" "${DEP_DATA}")"
EXISTING_SHA="$("${JQ}" -r ".${DEP}.sha256" "${DEP_DATA}")"
REPO="$(${JQ} -r ".${DEP}.repo" "${DEP_DATA}")"
URL="$(${JQ} -r ".${DEP}.url" "${DEP_DATA}")"
DEP_SEARCH="\"${DEP}\": {"
VERSION_SEARCH="\"version\": \"${EXISTING_VERSION}\","
SHA_SEARCH="\"sha256\": \"${EXISTING_SHA}\","

get_sha () {
    local url sha repo version url
    url="$1"
    repo="$2"
    version="$3"
    url="${url//\{repo\}/${repo}}"
    url="${url//\{version\}/${version}}"
    sha="$(curl -sfL "${url}" | sha256sum | cut -d' ' -f1)" || {
        echo "Failed to fetch asset (${url})" >&2
        exit 1
    }
    printf "$sha"
}

find_version_line () {
    # This needs to find the correct version to replace
    match="$(\
        grep -n "${DEP_SEARCH}" "${VERSION_FILE}" \
        | cut -d: -f-2)"
    match_ln="$(\
        echo "${match}" \
        | cut -d: -f1)"
    match_ln="$((match_ln + 1))"
    version_match_ln="$(\
        tail -n "+${match_ln}" "${VERSION_FILE}" \
        | grep -n "${VERSION_SEARCH}" \
        | head -n1 \
        | cut -d: -f1)"
    version_match_ln="$((match_ln + version_match_ln - 1))"
    printf "$version_match_ln"
}

find_sha_line () {
    # This needs to find the correct version to replace
    match="$(\
        grep -n "${DEP_SEARCH}" "${VERSION_FILE}" \
        | cut -d: -f-2)"
    match_ln="$(\
        echo "${match}" \
        | cut -d: -f1)"
    match_ln="$((match_ln + 1))"
    sha_match_ln="$(\
        tail -n "+${match_ln}" "${VERSION_FILE}" \
        | grep -n "${SHA_SEARCH}" \
        | head -n1 \
        | cut -d: -f1)"
    sha_match_ln="$((match_ln + sha_match_ln - 1))"
    printf "$sha_match_ln"
}

update_sha () {
    local match_ln search replace
    match_ln="$1"
    search="$2"
    replace="$3"
    echo "Updating sha: ${search} -> ${replace}"
    sed -i "${match_ln}s/${search}/${replace}/" "$VERSION_FILE"
}

update_version () {
    local match_ln search replace
    match_ln="$1"
    search="$2"
    replace="$3"
    echo "Updating version: ${search} -> ${replace}"
    sed -i "${match_ln}s/${search}/${replace}/" "$VERSION_FILE"
}

update_dependency () {
    local dep_ln sha
    dep_ln="$(find_version_line)"
    if [[ -z "$dep_ln" ]]; then
        echo "Dependency(${DEP}) not found in ${VERSION_FILE}" >&2
        exit 1
    fi
    sha="$(get_sha "${URL}" "${REPO}" "${VERSION}")"
    if [[ -z "$sha" ]]; then
        echo "Unable to resolve sha for ${DEP}/${VERSION}" >&2
        exit 1
    fi
    sha_ln="$(find_sha_line)"
    if [[ -z "$sha_ln" ]]; then
        echo "Unable to find sha for ${DEP}/${VERSION}" >&2
        exit 1
    fi
    update_version "${dep_ln}" "${EXISTING_VERSION}" "${VERSION}"
    update_sha "${sha_ln}" "${EXISTING_SHA}" "${sha}"
}

update_dependency
