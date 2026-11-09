#!/usr/bin/env bash
# //coverage:lcov_merger wrapping a fake merger (:fake_merger): argument pass-through,
# the stripped record set, and failure handling.
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-$TEST_SRCDIR}/$f"
MERGER="$(rlocation "$MERGER")"
LCOV_DATA="$(rlocation "$LCOV_DATA")"

WORK="$PWD/lcov-merger-test.${BASHPID}"
mkdir "$WORK"
trap 'rm -rf -- "$WORK"' EXIT

export FAKE_MERGER_ARGS="$WORK/args" FAKE_MERGER_RUNFILES="$WORK/runfiles" FAKE_MERGER_INPUT="$LCOV_DATA"

# Arguments pass through unchanged, in order, and the merger sees this tree as its runfiles.
"$MERGER" --coverage_dir="$WORK/cov dir" --output_file="$WORK/out.dat" \
    --filter_sources=/usr/bin/.+ --source_file_manifest="$WORK/manifest"
[[ "$(cat "$WORK/args")" == "--coverage_dir=$WORK/cov dir
--output_file=$WORK/out.dat
--filter_sources=/usr/bin/.+
--source_file_manifest=$WORK/manifest" ]]
[[ "$(cat "$WORK/runfiles")" == "${RUNFILES_DIR:-$TEST_SRCDIR}" ]]

# Function and branch records are gone, everything else is byte-identical and in order.
if grep -q -E '^(FN|FNDA|FNF|FNH|BRDA|BRF|BRH):' "$WORK/out.dat"; then
    echo "Stripped records survived" >&2
    exit 1
fi
diff <(grep -v -E '^(FN|FNDA|FNF|FNH|BRDA|BRF|BRH):' "$LCOV_DATA") "$WORK/out.dat"
# Zero-hit lines are kept.
grep -q '^DA:2,0$' "$WORK/out.dat"
grep -q '^SF:source/uncovered/uncovered.cc$' "$WORK/out.dat"
[[ "$(wc -l < "$WORK/out.dat")" == 12 ]]
[[ "$(grep -c '^end_of_record$' "$WORK/out.dat")" == "$(grep -c '^end_of_record$' "$LCOV_DATA")" ]]
# No staging file is left next to the report.
if compgen -G "$WORK/out.dat.strip.*" >/dev/null; then
    echo "Staging file left behind" >&2
    exit 1
fi

# Non-UTF-8 bytes do not turn the report into grep's "binary file" message.
printf 'SF:source/caf\xe9.cc\nFN:1,f\nDA:1,1\nend_of_record\n' > "$WORK/latin1.dat"
FAKE_MERGER_INPUT="$WORK/latin1.dat" "$MERGER" --output_file="$WORK/latin1_out.dat"
cmp <(printf 'SF:source/caf\xe9.cc\nDA:1,1\nend_of_record\n') "$WORK/latin1_out.dat"

# A report that is nothing but stripped records becomes empty rather than an error.
printf 'FN:1,f\nFNDA:1,f\nBRDA:1,0,0,1\n' > "$WORK/only_stripped.dat"
FAKE_MERGER_INPUT="$WORK/only_stripped.dat" "$MERGER" --output_file="$WORK/empty.dat"
[[ -f "$WORK/empty.dat" && ! -s "$WORK/empty.dat" ]]

# A merger that writes nothing (eg no coverage data) is not an error either.
FAKE_MERGER_INPUT='' "$MERGER" --output_file="$WORK/none.dat"
[[ ! -e "$WORK/none.dat" ]]

# Without --output_file there is nothing to filter: fail before running the merger.
rm -f "$WORK/args"
if "$MERGER" --coverage_dir="$WORK" 2>"$WORK/err"; then
    echo "Expected missing --output_file to fail" >&2
    exit 1
fi
grep -q -- '--output_file is required' "$WORK/err"
[[ ! -e "$WORK/args" ]]

# A failing merger fails the wrapper and leaves its output alone.
printf 'FN:1,f\nDA:1,1\n' > "$WORK/untouched.dat"
if FAKE_MERGER_EXIT=3 "$MERGER" --output_file="$WORK/untouched.dat" 2>"$WORK/err"; then
    echo "Expected merger failure to propagate" >&2
    exit 1
fi
grep -q 'merger exploded' "$WORK/err"
grep -q '^FN:1,f$' "$WORK/untouched.dat"
