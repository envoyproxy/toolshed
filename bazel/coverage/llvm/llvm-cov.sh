#!/usr/bin/env bash
# llvm-cov for Bazel's coverage postprocessing (`LLVM_COV`): a smaller, cheaper `export`.
#
# Bazel's collect_cc_coverage.sh runs `llvm-cov export -format=lcov` once per test over the
# whole instrumented binary, and the lcov merger then keeps only the files in the coverage
# manifest (the instrumented sources). For a large C++ test binary most of what the export
# writes never survives that:
#
# - function records (`FN`/`FNDA`: every function's mangled name) and branch records are the
#   bulk of the bytes and of the export's work, and the combined report validates line
#   coverage;
# - code pulled in from external repositories (`external/...` and the generated code under
#   `bazel-out/<config>/bin/external/...`) is ~85% of an Envoy test's export and is never in
#   the manifest, which lists workspace sources only.
#
# `export` therefore gets `-skip-functions -skip-branches` and an `-ignore-filename-regex`
# for external paths, which is a path match only, so nothing the merger would keep is lost.
# A consumer whose instrumented code lives in an external repository sets
# LLVM_COV_IGNORE_FILENAME_REGEX to a pattern of its own, or to the empty string to ignore
# nothing. Every other invocation goes through unchanged.
#
# The real tool is next to the toolchain's gcov (toolchains_llvm points `gcov` at
# llvm-profdata in the same bin/), which Bazel provides as COVERAGE_GCOV_PATH.
set -euo pipefail

[[ -n "${COVERAGE_GCOV_PATH:-}" ]] || { echo "ERROR: COVERAGE_GCOV_PATH is not set" >&2; exit 1; }
real="$(dirname "$COVERAGE_GCOV_PATH")/llvm-cov"
[[ -x "$real" ]] || { echo "ERROR: llvm-cov not found beside COVERAGE_GCOV_PATH: $real" >&2; exit 1; }

ignore="${LLVM_COV_IGNORE_FILENAME_REGEX-^(external|bazel-out/[^/]+/bin/external)/}"

if [[ $# -gt 0 && "$1" == "export" ]]; then
    shift
    if [[ -n "$ignore" ]]; then
        exec "$real" export -skip-functions -skip-branches "-ignore-filename-regex=$ignore" "$@"
    fi
    exec "$real" export -skip-functions -skip-branches "$@"
fi
exec "$real" "$@"
