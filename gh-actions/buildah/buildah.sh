#!/bin/bash -e

set -o pipefail


_buildah_command () {
    local buildah_command="${1}"
    local subcommand="${2}"
    _print_command "$@"
    shift 2
    if ! buildah manifest "${subcommand}" "$@" 2>/dev/null; then
        error="Buildah (${buildah_command}) failure: ${*}"
        echo "::error::${error}" >&2
        return 1
    fi
    echo "  ✓ ${buildah_command}: ${subcommand}"
    echo "::endgroup::"
}

_end_command () {
    echo "::endgroup::"
}

_print_command () {
    local buildah_command="${1}"
    local subcommand="${2}"
    shift 2
    echo "::group::${buildah_command}: ${subcommand}"
    for arg in "$@"; do
        echo "  ${arg}"
    done
}

handle_manifest () {
    local subcommand="${1}"
    if [[ "$subcommand" == "push" &&  "$DRY_RUN" == "true" ]]; then
        _print_command "[DRY RUN] manifest" "${@}"
        echo "::endgroup::"
        return
    fi
    _buildah_command manifest "${@}"
}

export -f handle_manifest
