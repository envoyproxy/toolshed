#!/usr/bin/env bash
# //coverage:lcov_merger as shipped: Bazel's Java merger launched from inside the wrapper's
# runfiles tree, in the way collect_coverage.sh invokes it.
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-$TEST_SRCDIR}/$f"
MERGER="$(rlocation "$MERGER")"
LCOV_DATA="$(rlocation "$LCOV_DATA")"

WORK="$PWD/lcov-merger-java-test.${BASHPID}"
mkdir -p "$WORK/coverage"
trap 'rm -rf -- "$WORK"' EXIT
cp "$LCOV_DATA" "$WORK/coverage/_cc_coverage.dat"
printf 'source/a/a.cc\nsource/uncovered/uncovered.cc\n' > "$WORK/manifest"

# Lay the merger out as Bazel stages a tool for an action: the executable with its own
# runfiles tree beside it. collect_coverage.sh clears the runfiles variables before exec-ing
# the merger, so this is the layout the wrapper has to find its tree from.
ln -s "$MERGER" "$WORK/lcov_merger"
ln -s "${RUNFILES_DIR:-$TEST_SRCDIR}" "$WORK/lcov_merger.runfiles"
env -u RUNFILES_DIR -u RUNFILES_MANIFEST_FILE -u JAVA_RUNFILES "$WORK/lcov_merger" \
    --coverage_dir="$WORK/coverage" --output_file="$WORK/coverage.dat" \
    --filter_sources=/usr/bin/.+ --source_file_manifest="$WORK/manifest"

[[ -s "$WORK/coverage.dat" ]]
if grep -q -E '^(FN|FNDA|FNF|FNH|BRDA|BRF|BRH):' "$WORK/coverage.dat"; then
    echo "Stripped records survived the real merger" >&2
    exit 1
fi
grep -q '^SF:source/a/a.cc$' "$WORK/coverage.dat"
grep -q '^SF:source/uncovered/uncovered.cc$' "$WORK/coverage.dat"
grep -q '^DA:1,1$' "$WORK/coverage.dat"
grep -q '^DA:2,0$' "$WORK/coverage.dat"
[[ "$(grep -c '^end_of_record$' "$WORK/coverage.dat")" == 2 ]]
# The intermediates the merger read are gone (this is the in-test-action case).
[[ -z "$(ls -A "$WORK/coverage")" ]]
