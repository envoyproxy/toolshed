#!/usr/bin/env bash
# Per-test lcov merger (`--coverage_output_generator`) that strips the records the
# combined report does not read.
#
# Bazel runs the merger once per test (in the coverage postprocessing spawn) to turn the
# raw coverage data into the test's `coverage.dat`. Every one of those files describes
# the whole instrumented binary, and in a large C++ tree most of the bytes are function
# (`FN`/`FNDA`) and branch (`BRDA`) records: thousands of mangled names per file, repeated
# for every test. Line coverage, which is what the thresholds are validated against, is a
# small fraction. Stripping the rest shrinks every per-test file several-fold before it is
# uploaded, downloaded and merged into the combined report.
#
# Zero-hit `DA` lines are kept: the baseline report only lists files, so a line no test
# hits would otherwise disappear from the combined report rather than count as uncovered.
#
# When the merger runs inside the test action itself (no split postprocessing), the
# coverage directory it reads is one of the test's output directories, and everything in it
# is uploaded with the test's results: the raw profile, the unfiltered `llvm-cov export`
# and the indexed profile, several hundred MB per test that nothing reads again once the
# report is merged. The merger is the last step of that pipeline, so it removes them.
# In a split postprocessing spawn (IS_COVERAGE_SPAWN=1) the directory is an input of a
# separate action and is left alone.
#
# Arguments are passed through unchanged to Bazel's merger. The merged report is filtered
# in place afterwards, so the wrapper is transparent to `collect_coverage.sh`.

set -euo pipefail

# Bazel 7 runs this merger inside the test action (no split postprocessing) with neither a
# runfiles tree nor Bazel's own merger staged beside it. That case is detected here and
# handled by the built-in merge below.
HAVE_RUNFILES=1
# --- begin runfiles.bash initialization v3 ---
f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
  source "$0.runfiles/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null ||
  HAVE_RUNFILES=0
# --- end runfiles.bash initialization v3 ---

fail() { echo "ERROR: $*" >&2; exit 1; }

# Substituted at analysis time.
MERGER_RLOCATION="{{MERGER}}"
STRIP_RECORDS="{{STRIP}}"
CLEAN_COVERAGE_DIR="{{CLEAN}}"

output_file=
coverage_dir=
source_file_manifest=
sources_to_replace_file=
filter_sources=()
for arg in "$@"; do
    case "$arg" in
        --output_file=*) output_file="${arg#*=}" ;;
        --coverage_dir=*) coverage_dir="${arg#*=}" ;;
        --source_file_manifest=*) source_file_manifest="${arg#*=}" ;;
        --sources_to_replace_file=*) sources_to_replace_file="${arg#*=}" ;;
        --filter_sources=*) filter_sources+=("${arg#*=}") ;;
    esac
done
[[ -n "$output_file" ]] || fail "--output_file is required"
[[ -n "$STRIP_RECORDS" ]] || fail "No records configured to strip"

# The built-in merge, for when Bazel's merger is not available (see above). It does what
# Bazel's merger does with the C++ lcov that collect_cc_coverage.sh leaves in the coverage
# directory: renames reported sources to their actual paths, drops the sources matching
# --filter_sources, and keeps only the sources in the source file manifest (the instrumented
# sources). Function and branch records are stripped afterwards as for Bazel's merger.
builtin_merge() {
    [[ -n "$coverage_dir" && -d "$coverage_dir" ]] || return 0
    local inputs=()
    while IFS= read -r -d '' f; do
        inputs+=("$f")
    done < <(find "$coverage_dir" -name '*.dat' -type f -print0 | LC_ALL=C sort -z)
    [[ ${#inputs[@]} -gt 0 ]] || return 0
    local filter=""
    if [[ ${#filter_sources[@]} -gt 0 ]]; then
        filter="^($(IFS='|'; echo "${filter_sources[*]}"))$"
    fi
    LC_ALL=C awk \
        -v manifest="${source_file_manifest}" \
        -v replace="${sources_to_replace_file}" \
        -v filter="$filter" '
        BEGIN {
            if (manifest != "") {
                while ((getline line < manifest) > 0) keep[line] = 1
                close(manifest)
            }
            if (replace != "") {
                while ((getline line < replace) > 0) {
                    i = index(line, ":")
                    if (i > 0) actual[substr(line, 1, i - 1)] = substr(line, i + 1)
                }
                close(replace)
            }
        }
        /^SF:/ {
            src = substr($0, 4)
            if (src in actual) src = actual[src]
            emit = !(filter != "" && src ~ filter) && (manifest == "" || src in keep)
            if (emit) print "SF:" src
            next
        }
        /^TN:/ { next }
        emit { print }
        /^end_of_record$/ { emit = 0 }
    ' "${inputs[@]}" > "$output_file"
}

# Without a runfiles tree, or with a test's runfiles tree that does not carry Bazel's merger
# (as when Bazel 7 runs this inside the test action), merge with the built-in merge instead.
merger=
if [[ "$HAVE_RUNFILES" == 1 ]]; then
    merger="$(rlocation "$MERGER_RLOCATION" 2>/dev/null)" || merger=
    [[ -n "$merger" && -e "$merger" ]] || merger=
fi

if [[ -n "$merger" ]]; then
    # Bazel's merger is a java_binary inside this binary's runfiles tree. Its launcher looks
    # for its own tree next to itself unless told where to look.
    runfiles_root="${RUNFILES_DIR:-}"
    if [[ -z "$runfiles_root" && -d "$0.runfiles" ]]; then
        runfiles_root="$0.runfiles"
    fi
    if [[ -n "$runfiles_root" ]]; then
        export RUNFILES_DIR="$runfiles_root"
        export JAVA_RUNFILES="$runfiles_root"
    fi
    "$merger" "$@"
else
    builtin_merge
fi

if [[ "$CLEAN_COVERAGE_DIR" == 1 && "${IS_COVERAGE_SPAWN:-}" != 1 && -n "$coverage_dir" && -d "$coverage_dir" ]]; then
    if [[ -f "$output_file" ]]; then
        # Should Bazel have placed the merged report inside the directory.
        find "$coverage_dir" -mindepth 1 -maxdepth 1 ! -samefile "$output_file" -exec rm -rf -- {} +
    else
        find "$coverage_dir" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
    fi
fi

[[ -f "$output_file" ]] || exit 0

# `^(FN|FNDA|...):` from the configured list.
pattern="^(${STRIP_RECORDS// /|}):"
filtered="${output_file}.strip.$$"
trap 'rm -f -- "$filtered"' EXIT
# Byte-wise, locale-independent: a stray non-UTF-8 byte must not turn the report into
# grep's "binary file matches" message. grep exits 1 when nothing survives; an empty
# report is still a valid report.
LC_ALL=C grep -a -v -E "$pattern" "$output_file" > "$filtered" || [[ $? -eq 1 ]]
mv -f "$filtered" "$output_file"
