#!/usr/bin/env bash

set -euo pipefail

# shellcheck disable=SC1090
source "$1"
unset BUILD_WORKSPACE_DIRECTORY SRCDIR FUZZ_COVERAGE VALIDATE_COVERAGE COVERAGE_TARGET
unset COVERAGE_VALIDATE_TARGET COVERAGE_ZSTD_TARGET BAZEL_GRPC_LOG
unset BAZEL_BUILD_OPTION_LIST BAZEL_QUERY_OPTION_LIST

parse_args --no-validate
[[ "${TARGETS[*]}" == //test/... ]]
[[ "$OUTPUT_DIR" == "$PWD/generated/coverage" ]]
[[ "$FUZZ" == false && "$VALIDATE" == false && "$SUMMARY_ONLY" == false ]]

if parse_args 2>/dev/null; then
    echo "Expected missing validation target to fail" >&2
    exit 1
fi
if parse_args --no-validate --unknown 2>/dev/null; then
    echo "Expected unknown option to fail" >&2
    exit 1
fi

export BUILD_WORKSPACE_DIRECTORY=/workspace SRCDIR=/ignored
export FUZZ_COVERAGE=true VALIDATE_COVERAGE=false COVERAGE_TARGET="//fallback/... //other/..."
export BAZEL_BUILD_OPTION_LIST="--jobs=2 --keep_going"
export BAZEL_QUERY_OPTION_LIST="--keep_going"
export BAZEL_GRPC_LOG=/env/log
parse_args
[[ "$WORKSPACE" == /workspace && "$OUTPUT_DIR" == /workspace/generated/fuzz_coverage ]]
[[ "${TARGETS[*]}" == "//fallback/... //other/..." ]]
[[ "${BUILD_OPTIONS[*]}" == "--jobs=2 --keep_going" ]]
[[ "${QUERY_OPTIONS[*]}" == --keep_going && "$GRPC_LOG" == /env/log ]]

export VALIDATE_COVERAGE=true COVERAGE_VALIDATE_TARGET=//env:validate
parse_args --fuzz --summary-only --config=coverage --config=extra \
    --validate-config=fuzz-config --validate-config=extra-config \
    --validate-target=//custom:validate --output-dir=custom \
    --bazel-opt=--jobs=3 --query-opt=--output=label --grpc-log=/flag/log \
    --fuzz-tag=custom_fuzz -- //custom/... //second/...
[[ "$FUZZ" == true && "$SUMMARY_ONLY" == true ]]
[[ "$VALIDATE_TARGET" == //custom:validate && "$OUTPUT_DIR" == /workspace/custom ]]
[[ "${CONFIGS[*]}" == "--config=coverage --config=extra" ]]
[[ "${VALIDATE_CONFIGS[*]}" == "--config=fuzz-config --config=extra-config" ]]
[[ "${BUILD_OPTIONS[*]}" == "--jobs=2 --keep_going --jobs=3" ]]
[[ "${QUERY_OPTIONS[*]}" == "--keep_going --output=label" ]]
[[ "$GRPC_LOG" == /flag/log && "$FUZZ_TAG" == custom_fuzz ]]
[[ "${TARGETS[*]}" == "//custom/... //second/..." ]]

unset BUILD_WORKSPACE_DIRECTORY
parse_args --output-dir=/absolute
[[ "$WORKSPACE" == /ignored && "$OUTPUT_DIR" == /absolute ]]

export SRCDIR=relative
parse_args
[[ "$WORKSPACE" == "$PWD/relative" && "$OUTPUT_DIR" == "$PWD/relative/generated/fuzz_coverage" ]]
