#!/usr/bin/env bash

set -euo pipefail

parse_args() {
    WORKSPACE="${BUILD_WORKSPACE_DIRECTORY:-${SRCDIR:-$PWD}}"
    [[ "$WORKSPACE" == /* ]] || WORKSPACE="$PWD/$WORKSPACE"
    FUZZ="${FUZZ_COVERAGE:-false}"
    VALIDATE="${VALIDATE_COVERAGE:-true}"
    SUMMARY_ONLY=false
    OUTPUT_DIR=""
    VALIDATE_TARGET="${COVERAGE_VALIDATE_TARGET:-}"
    ZSTD_TARGET="${COVERAGE_ZSTD_TARGET:-@zstd//:zstd_cli}"
    GRPC_LOG="${BAZEL_GRPC_LOG:-}"
    FUZZ_TAG=fuzz_target
    TARGETS=()
    CONFIGS=()
    VALIDATE_CONFIGS=()
    read -r -a BUILD_OPTIONS <<< "${BAZEL_BUILD_OPTION_LIST:-}"
    read -r -a QUERY_OPTIONS <<< "${BAZEL_QUERY_OPTION_LIST:-}"

    while (( $# )); do
        case "$1" in
            --fuzz) FUZZ=true ;;
            --summary-only) SUMMARY_ONLY=true ;;
            --no-validate) VALIDATE=false ;;
            --config=*) CONFIGS+=("$1") ;;
            --validate-config=*) VALIDATE_CONFIGS+=("--config=${1#*=}") ;;
            --output-dir=*) OUTPUT_DIR="${1#*=}" ;;
            --validate-target=*) VALIDATE_TARGET="${1#*=}" ;;
            --bazel-opt=*) BUILD_OPTIONS+=("${1#*=}") ;;
            --query-opt=*) QUERY_OPTIONS+=("${1#*=}") ;;
            --grpc-log=*) GRPC_LOG="${1#*=}" ;;
            --fuzz-tag=*) FUZZ_TAG="${1#*=}" ;;
            --) shift; TARGETS+=("$@"); break ;;
            --*) echo "ERROR: Unknown option: $1" >&2; return 1 ;;
            *) TARGETS+=("$1") ;;
        esac
        shift
    done
    if (( ${#TARGETS[@]} == 0 )); then
        if [[ -n "${COVERAGE_TARGET:-}" ]]; then
            read -r -a TARGETS <<< "$COVERAGE_TARGET"
        else
            TARGETS=(//test/...)
        fi
    fi
    if [[ -z "$OUTPUT_DIR" ]]; then
        OUTPUT_DIR=generated/coverage
        [[ "$FUZZ" != true ]] || OUTPUT_DIR=generated/fuzz_coverage
    fi
    [[ "$OUTPUT_DIR" == /* ]] || OUTPUT_DIR="$WORKSPACE/$OUTPUT_DIR"
    if [[ "$VALIDATE" != false && -z "$VALIDATE_TARGET" ]]; then
        echo "ERROR: Set --validate-target or COVERAGE_VALIDATE_TARGET (or --no-validate)" >&2
        return 1
    fi
    if [[ -z "$FUZZ_TAG" || "$FUZZ_TAG" == *"'"* || "$FUZZ_TAG" == *\\* || "$FUZZ_TAG" == *$'\n'* ]]; then
        echo "ERROR: --fuzz-tag must be a nonempty Bazel query pattern without quotes or backslashes" >&2
        return 1
    fi
}

run_coverage() {
    parse_args "$@"
    cd "$WORKSPACE"
    WORKSPACE="$PWD"
    if [[ "$FUZZ" == true ]]; then
        local selected
        selected="$(bazel query "${QUERY_OPTIONS[@]}" \
            --noshow_loading_progress --noshow_progress \
            "attr('tags', '$FUZZ_TAG', set(${TARGETS[*]}))")"
        TARGETS=()
        while IFS= read -r target; do
            [[ -z "$target" ]] || TARGETS+=("$target")
        done <<< "$selected"
        if (( ${#TARGETS[@]} == 0 )); then
            echo "ERROR: No coverage targets match fuzz tag: $FUZZ_TAG" >&2
            return 1
        fi
    fi
    local options=(--heap_dump_on_oom --experimental_ui_max_stdouterr_bytes=80000000)
    [[ -z "$GRPC_LOG" ]] || options+=("--remote_grpc_log=$GRPC_LOG")
    local report="$PWD/bazel-out/_coverage/_coverage_report.dat"
    rm -f "$report"
    bazel coverage "${BUILD_OPTIONS[@]}" "${options[@]}" "${CONFIGS[@]}" "${TARGETS[@]}"

    if [[ ! -s "$report" ]]; then
        echo "ERROR: Coverage report missing or empty: $report" >&2
        return 1
    fi
    local archive="${report%.dat}.tar.zst"
    mv -f "$report" "$archive"
    mkdir -p "$OUTPUT_DIR"
    bazel run "${BUILD_OPTIONS[@]}" --nobuild_tests_only "$ZSTD_TARGET" -- -d -c "$archive" \
        | tar -xf - -C "$OUTPUT_DIR"
    if [[ "$VALIDATE" != false ]]; then
        local args=("$OUTPUT_DIR/coverage.json")
        [[ "$SUMMARY_ONLY" != true ]] || args+=(--summary-only)
        bazel run "${BUILD_OPTIONS[@]}" "${VALIDATE_CONFIGS[@]}" \
            --nobuild_tests_only "$VALIDATE_TARGET" -- "${args[@]}"
    fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    run_coverage "$@"
fi
