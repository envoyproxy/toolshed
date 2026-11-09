#!/usr/bin/env bash
# Stands in for Bazel's lcov merger: records its arguments and runfiles, and writes the
# file named by FAKE_MERGER_INPUT to --output_file (nothing when it is unset or empty).
set -euo pipefail
printf '%s\n' "$@" > "${FAKE_MERGER_ARGS}"
printf '%s\n' "${JAVA_RUNFILES:-unset}" > "${FAKE_MERGER_RUNFILES}"
[[ -n "${FAKE_MERGER_EXIT:-}" ]] && { echo "merger exploded" >&2; exit "$FAKE_MERGER_EXIT"; }
for arg in "$@"; do
    case "$arg" in
        --output_file=*)
            [[ -z "${FAKE_MERGER_INPUT:-}" ]] || cp "$FAKE_MERGER_INPUT" "${arg#*=}"
            ;;
    esac
done
