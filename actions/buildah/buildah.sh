#!/bin/bash -e

set -o pipefail


# Tunables (overridable from the workflow env).
: "${BUILDAH_RETRY_MAX:=3}"          # total attempts for retryable subcommands
: "${BUILDAH_RETRY_DELAY:=5}"        # base delay (seconds), doubled each attempt
: "${BUILDAH_LOG_LEVEL:=warn}"       # buildah --log-level; bump to info/debug for triage
: "${BUILDAH_ERROR_TAIL_LINES:=40}"  # max lines of buildah output in annotation tail
: "${BUILDAH_PUSH_JOBS:=1}"          # concurrent `manifest push`es (1: each in turn)

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
    # Tee stdout and stderr to both the live log group (so they stream, stderr
    # on stderr) and a file (so we can include it in the ::error:: summary).
    # Pipelines rather than process substitutions, so both copies are complete
    # when this returns (a concurrent push's output is collected once it has).
    # With `pipefail`, the status is buildah's.
    {
        buildah --log-level "${BUILDAH_LOG_LEVEL}" "$@" 2>&1 1>&3 3>&- \
            | tee -a "${logfile}" >&2 3>&-
    } 3>&1 | tee -a "${logfile}"
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

# Concurrent pushes (`BUILDAH_PUSH_JOBS` > 1): each runs in the background, with its output (and
# any failure annotation) captured, and printed when it completes. A push only follows the
# `create`/`add`s of its manifest list, which run in turn before it.
#
# Each push writes its exit code to `<log>.rc` when it completes, which is how its completion is
# found (rather than `wait -n`, which does not report a push that completed before it was called).
_PUSH_PIDS=()
declare -A _PUSH_LOGS=()
_PUSH_RC=0

# Wait for at least one push to complete; print the output of each that has, and record any
# failure.
_push_reap () {
    local pid rc remaining=() reaped=0
    while (( reaped == 0 )); do
        remaining=()
        for pid in "${_PUSH_PIDS[@]}"; do
            if [[ -s "${_PUSH_LOGS[${pid}]}.rc" ]]; then
                wait "${pid}" 2> /dev/null || :
                rc="$(< "${_PUSH_LOGS[${pid}]}.rc")"
            elif ! kill -0 "${pid}" 2> /dev/null; then
                # It exited without its marker (which it writes on exit, so eg killed): its exit
                # status, as a failure in any case.
                rc=0
                wait "${pid}" 2> /dev/null || rc=$?
                if [[ -s "${_PUSH_LOGS[${pid}]}.rc" ]]; then
                    rc="$(< "${_PUSH_LOGS[${pid}]}.rc")"
                elif (( rc == 0 )); then
                    rc=1
                fi
            else
                remaining+=("${pid}")
                continue
            fi
            cat "${_PUSH_LOGS[${pid}]}" 2> /dev/null || :
            rm -f "${_PUSH_LOGS[${pid}]}" "${_PUSH_LOGS[${pid}]}.rc"
            unset "_PUSH_LOGS[${pid}]"
            if (( rc != 0 )); then
                _PUSH_RC="${rc}"
            fi
            reaped=$(( reaped + 1 ))
        done
        _PUSH_PIDS=("${remaining[@]}")
        if (( reaped == 0 )); then
            sleep 0.1
        fi
    done
}

# On exit (eg an operation failing, with `set -e`, before `handle_manifest_wait`), collect the
# pushes still running, so their output and any failure annotations are printed, and keep the
# exit status.
_push_drain_on_exit () {
    local rc=$?
    trap - EXIT
    if (( ${#_PUSH_PIDS[@]} > 0 )); then
        handle_manifest_wait || :
    fi
    exit "${rc}"
}

_push_background () {
    local logfile
    if (( ${#_PUSH_LOGS[@]} == 0 )); then
        trap _push_drain_on_exit EXIT
    fi
    while (( ${#_PUSH_PIDS[@]} >= BUILDAH_PUSH_JOBS )); do
        _push_reap
    done
    logfile="$(mktemp -t buildah-push.XXXXXX)"
    # The push writes its exit status on exit, however it exits (eg aborted by `set -u`).
    (
        trap 'echo "$?" > "${logfile}.rc"' EXIT
        _buildah_command manifest "${@}" > "${logfile}" 2>&1
    ) &
    _PUSH_PIDS+=("$!")
    _PUSH_LOGS[$!]="${logfile}"
    echo "Started: manifest ${*}"
}

# Wait for the concurrent pushes, and fail if any did.
handle_manifest_wait () {
    while (( ${#_PUSH_PIDS[@]} > 0 )); do
        _push_reap
    done
    return "${_PUSH_RC}"
}

handle_manifest () {
    local subcommand="${1}"
    if [[ "${subcommand}" == "push" && "${DRY_RUN}" == "true" ]]; then
        _print_command "[DRY RUN] manifest" "${@}"
        _end_command
        return
    fi
    if [[ ! "${BUILDAH_PUSH_JOBS}" =~ ^[1-9][0-9]*$ ]]; then
        echo "::error::push-jobs must be a positive integer, not: ${BUILDAH_PUSH_JOBS}"
        return 1
    fi
    if [[ "${subcommand}" == "push" ]] && (( BUILDAH_PUSH_JOBS > 1 )); then
        _push_background "${@}"
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

export -f handle_manifest handle_manifest_wait
