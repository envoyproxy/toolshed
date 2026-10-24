#!/usr/bin/env bash

set -euo pipefail

# shellcheck disable=SC1090
source "$1"
unset BUILD_WORKSPACE_DIRECTORY SRCDIR FUZZ_COVERAGE VALIDATE_COVERAGE COVERAGE_TARGET
unset COVERAGE_VALIDATE_TARGET COVERAGE_ZSTD_TARGET BAZEL_GRPC_LOG
unset BAZEL_BUILD_OPTION_LIST BAZEL_QUERY_OPTION_LIST

export SRCDIR="$TEST_TMPDIR/workspace"
mkdir -p "$SRCDIR/bazel-out/_coverage" "$TEST_TMPDIR/payload"
printf '{"summary":{}}\n' >"$TEST_TMPDIR/payload/coverage.json"
tar -cf "$TEST_TMPDIR/payload.tar" -C "$TEST_TMPDIR/payload" .
log="$TEST_TMPDIR/commands"

# Mock the external command at the shell boundary; the parser remains unchanged.
# BAZEL_MOCK selects the scenario: "ok" produces a report, "empty" does not.
BAZEL_MOCK=ok
bazel() {
    if [[ "$BAZEL_MOCK" == empty ]]; then
        case "$1" in
            query) return 0 ;;
            coverage) : >"$SRCDIR/bazel-out/_coverage/_coverage_report.dat" ;;
            *) echo "Unexpected command after empty report/query" >&2; exit 1 ;;
        esac
        return 0
    fi
    printf '%s\n' "$*" >>"$log"
    case "$1" in
        query) printf '//source:a_test\n//source:b_test\n' ;;
        coverage)
            [[ ! -e "$SRCDIR/bazel-out/_coverage/_coverage_report.dat" ]]
            printf 'compressed report\n' >"$SRCDIR/bazel-out/_coverage/_coverage_report.dat"
            ;;
        run)
            if [[ "$*" == *" -d -c "* ]]; then
                cat "$TEST_TMPDIR/payload.tar"
            fi
            ;;
        *) return 1 ;;
    esac
}

printf 'stale report\n' >"$SRCDIR/bazel-out/_coverage/_coverage_report.dat"
run_coverage --fuzz --summary-only --config=coverage --validate-config=validate \
    --validate-target=//custom:validate --grpc-log=grpc.log //source/... //test/...
[[ -f "$SRCDIR/generated/fuzz_coverage/coverage.json" ]]
grep -Fqx "query --noshow_loading_progress --noshow_progress attr('tags', 'fuzz_target', set(//source/... //test/...))" "$log"
grep -Fqx "coverage --heap_dump_on_oom --experimental_ui_max_stdouterr_bytes=80000000 --remote_grpc_log=grpc.log --config=coverage //source:a_test //source:b_test" "$log"
grep -Fqx "run --config=validate --nobuild_tests_only //custom:validate -- $SRCDIR/generated/fuzz_coverage/coverage.json --summary-only" "$log"
grep -Fqx "run --nobuild_tests_only @zstd//:zstd_cli -- -d -c $SRCDIR/bazel-out/_coverage/_coverage_report.tar.zst" "$log"

: >"$log"
run_coverage --no-validate
[[ "$(wc -l <"$log")" -eq 2 ]]
[[ -f "$SRCDIR/generated/coverage/coverage.json" ]]

BAZEL_MOCK=empty
if (run_coverage --no-validate) 2>/dev/null; then
    echo "Expected empty coverage report to fail" >&2
    exit 1
fi
if (run_coverage --no-validate --fuzz) 2>/dev/null; then
    echo "Expected empty fuzz query to fail" >&2
    exit 1
fi
