#!/bin/bash -e

set -o pipefail


# Tunables (overridable from the workflow env).
: "${BUILDAH_RETRY_MAX:=3}"          # total attempts for retryable subcommands
: "${BUILDAH_RETRY_DELAY:=5}"        # base delay (seconds), doubled each attempt
: "${BUILDAH_LOG_LEVEL:=warn}"       # buildah --log-level; bump to info/debug for triage
: "${BUILDAH_ERROR_TAIL_LINES:=40}"  # max lines of buildah output in annotation tail

# Subcommands we are willing to retry. `create`/`add` are local and not worth
# retrying; `push` talks to a registry and is the one that flakes.
_BUILDAH_RETRYABLE_SUBCOMMANDS=("push")


_print_command () {
    local buildah_command="${1}"
    local subcommand="${2}"
    shift 2
    echo "::group::${buildah_command}: ${subcommand}"
    for arg in "$@"; do
        echo "  ${arg}"
    done
}

_end_command () {
    echo "::endgroup::"
}

_is_retryable () {
    local subcommand="${1}"
    local s
    for s in "${_BUILDAH_RETRYABLE_SUBCOMMANDS[@]}"; do
        [[ "${s}" == "${subcommand}" ]] && return 0
    done
    return 1
}

# Map an exit status to a short human-readable reason. We care particularly
# about signal exits (128+N) so a real segfault is not hidden behind "exit 1".
_describe_exit () {
    local code="${1}"
    case "${code}" in
        0)   echo "ok" ;;
        139) echo "exit=139 (SIGSEGV / segmentation fault)" ;;
        137) echo "exit=137 (SIGKILL / OOM?)" ;;
        134) echo "exit=134 (SIGABRT)" ;;
        143) echo "exit=143 (SIGTERM)" ;;
        *)
            if (( code > 128 )); then
                echo "exit=${code} (signal $((code - 128)))"
            else
                echo "exit=${code}"
            fi
            ;;
    esac
}

# Run a single buildah invocation. Captures stderr so we can emit it as part
# of the failure annotation rather than dropping it on the floor.
_run_buildah_once () {
    local logfile="${1}"
    shift
    # Tee stderr to both the live log group (so it streams) and a file (so we
    # can include it in the ::error:: summary).
    buildah --log-level "${BUILDAH_LOG_LEVEL}" "$@" \
        > >(tee -a "${logfile}") \
        2> >(tee -a "${logfile}" >&2)
}

_buildah_command () {
    local buildah_command="${1}"
    local subcommand="${2}"
    _print_command "$@"
    shift 2

    local logfile
    logfile="$(mktemp -t buildah.XXXXXX)"

    local attempt=1
    local max=1
    if _is_retryable "${subcommand}"; then
        max="${BUILDAH_RETRY_MAX}"
    fi

    local delay="${BUILDAH_RETRY_DELAY}"
    local rc=0

    while : ; do
        : > "${logfile}"
        rc=0
        _run_buildah_once "${logfile}" manifest "${subcommand}" "$@" || rc=$?

        if (( rc == 0 )); then
            echo "  ✓ ${buildah_command}: ${subcommand}"
            _end_command
            rm -f "${logfile}"
            return 0
        fi

        local reason
        reason="$(_describe_exit "${rc}")"
        echo "  ✗ attempt ${attempt}/${max} failed: ${reason}"

        if (( attempt >= max )); then
            break
        fi

        echo "  ↻ retrying in ${delay}s ..."
        sleep "${delay}"
        delay=$(( delay * 2 ))
        attempt=$(( attempt + 1 ))
    done

    # Emit a multi-line GH annotation. The %0A escape preserves newlines in
    # the rendered annotation; the raw log is also already visible in-group.
    local tail
    tail="$(tail -n "${BUILDAH_ERROR_TAIL_LINES}" "${logfile}" | sed 's/%/%25/g; s/\r/%0D/g; s/$/%0A/' | tr -d '\n')"
    echo "::error title=Buildah ${buildah_command} ${subcommand} failed::${buildah_command} ${subcommand} $* :: $(_describe_exit "${rc}")%0A----- buildah output (tail) -----%0A${tail}"
    rm -f "${logfile}"
    _end_command
    return "${rc}"
}

handle_manifest () {
    local subcommand="${1}"
    if [[ "${subcommand}" == "push" && "${DRY_RUN}" == "true" ]]; then
        _print_command "[DRY RUN] manifest" "${@}"
        _end_command
        return
    fi
    _buildah_command manifest "${@}"
}

# Useful one-off diagnostic; cheap, and pinpoints runner-image bumps.
_print_command buildah version
if ! buildah version; then
    echo "::warning::Unable to run 'buildah version'" >&2
fi
_end_command

export -f handle_manifest
