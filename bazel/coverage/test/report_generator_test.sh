#!/usr/bin/env bash
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-$TEST_SRCDIR}/$f"
GENERATOR="$(rlocation "$GENERATOR")"
CUSTOM_GENERATOR="$(rlocation "$CUSTOM_GENERATOR")"
JQ_BIN="$(rlocation "$JQ_BIN")"
ZSTD_BIN="$(rlocation "$ZSTD_BIN")"
LCOV_DATA="$(rlocation "$LCOV_DATA")"

# Stay in the sandbox workspace, not a shared temporary directory.
WORK="$PWD/report-generator-test.${BASHPID}"
mkdir "$WORK"
trap 'rm -rf -- "$WORK"' EXIT
mkdir "$WORK/execroot" "$WORK/output"
cp -RL "$(dirname "$LCOV_DATA")/ws" "$WORK/ws"
printf 'keep me\n' > "$WORK/output/sentinel"
cp "$LCOV_DATA" "$WORK/input data.dat"
# A missing entry and an unterminated final line are intentional.
printf '%s\n%s' "$WORK/missing.dat" "$WORK/input data.dat" > "$WORK/reports.txt"

check_archive() {
    local archive="$1" destination="$2"
    mkdir "$destination"
    "$ZSTD_BIN" -dc "$archive" | tar -xf - -C "$destination"
    [[ -s "$destination/html/index.html" && -s "$destination/html/source/a/a.cc.html" ]]
    [[ ! -e "$destination/html/badges" && ! -e "$destination/html/coverage.json" ]]
    "$JQ_BIN" -e '
      .summary.coverage_percent == 50
      and .summary.threshold_reached
      and .source_directories == ["source/a", "source/uncovered"]
      and .validation.failed_coverage == []
      and .validation.excellent_coverage[0].directory == "source/a"
    ' "$destination/coverage.json" >/dev/null
}

BUILD_WORKSPACE_DIRECTORY="$WORK/ws" "$GENERATOR" \
    --reports_file="$WORK/reports.txt" --output_file="$WORK/report.tar.zst"
check_archive "$WORK/report.tar.zst" "$WORK/extracted"
[[ "$(cat "$WORK/output/sentinel")" == "keep me" ]]
[[ ! -e "$WORK/input data.info" ]]

# Coverage's execroot invocation has no BUILD_WORKSPACE_DIRECTORY. Only the
# source-root symlink is available (no MODULE/WORKSPACE or source config).
ln -s "$WORK/ws/source" "$WORK/execroot/source"
(
    cd "$WORK/execroot"
    unset BUILD_WORKSPACE_DIRECTORY
    "$GENERATOR" --reports_file "$WORK/reports.txt" --output_file "$WORK/fallback.tar.zst"
)
check_archive "$WORK/fallback.tar.zst" "$WORK/fallback-extracted"

# Bazel can also materialize real source directories containing file symlinks.
mkdir -p "$WORK/file-execroot/source/a"
ln -s "$WORK/ws/source/a/a.cc" "$WORK/file-execroot/source/a/a.cc"
(
    cd "$WORK/file-execroot"
    unset BUILD_WORKSPACE_DIRECTORY
    "$GENERATOR" --reports_file "$WORK/reports.txt" --output_file "$WORK/file-fallback.tar.zst"
)
check_archive "$WORK/file-fallback.tar.zst" "$WORK/file-fallback-extracted"

# A copied source tree does not identify the real workspace. Never silently
# treat an unresolved execroot as the source workspace.
mkdir -p "$WORK/unresolved-execroot/source/a"
cp "$WORK/ws/source/a/a.cc" "$WORK/unresolved-execroot/source/a/a.cc"
if (
    cd "$WORK/unresolved-execroot"
    unset BUILD_WORKSPACE_DIRECTORY
    "$GENERATOR" --reports_file "$WORK/reports.txt" --output_file "$WORK/unresolved.tar.zst"
) > "$WORK/error" 2>&1; then
    echo "Generator unexpectedly treated an unresolved execroot as a workspace" >&2
    exit 1
fi
grep -q 'Cannot resolve source files to a real workspace' "$WORK/error"

BUILD_WORKSPACE_DIRECTORY="$WORK/does-not-exist" "$GENERATOR" \
    --workspace "$WORK/ws" --reports_file "$WORK/reports.txt" --output_file "$WORK/override.tar.zst"
check_archive "$WORK/override.tar.zst" "$WORK/override-extracted"

BUILD_WORKSPACE_DIRECTORY="$WORK/does-not-exist" "$GENERATOR" \
    --workspace="$WORK/ws" --reports_file="$WORK/reports.txt" --output_file="$WORK/equals-override.tar.zst"
check_archive "$WORK/equals-override.tar.zst" "$WORK/equals-override-extracted"

# Exercise manifest-only runfiles resolution, including imported jq modules.
manifest="${RUNFILES_MANIFEST_FILE:-${RUNFILES_DIR:-$TEST_SRCDIR}/MANIFEST}"
if [[ -f "$manifest" ]]; then
    (
        unset RUNFILES_DIR
        export RUNFILES_MANIFEST_FILE="$manifest"
        BUILD_WORKSPACE_DIRECTORY="$WORK/ws" "$GENERATOR" \
            --reports_file "$WORK/reports.txt" --output_file "$WORK/manifest.tar.zst"
    )
    check_archive "$WORK/manifest.tar.zst" "$WORK/manifest-extracted"
fi

# Custom templates are generated files in three distinct directories, with
# filenames unrelated to the canonical template names. Exercise nested source
# roots and a non-default source pattern in an execroot-only invocation too.
mkdir -p "$WORK/custom-ws/nested/source/a" "$WORK/custom-execroot/nested" "$WORK/custom-extracted"
cp "$WORK/ws/source/a/a.cc" "$WORK/custom-ws/nested/source/a/a.cpp"
sed 's|source/a/a.cc|nested/source/a/a.cpp|' "$LCOV_DATA" > "$WORK/custom.dat"
printf '%s\n' "$WORK/custom.dat" > "$WORK/custom-reports"
ln -s "$WORK/custom-ws/nested/source" "$WORK/custom-execroot/nested/source"
(
    cd "$WORK/custom-execroot"
    unset BUILD_WORKSPACE_DIRECTORY
    "$CUSTOM_GENERATOR" --reports_file "$WORK/custom-reports" --output_file "$WORK/custom.tar.zst"
)
"$ZSTD_BIN" -dc "$WORK/custom.tar.zst" | tar -xf - -C "$WORK/custom-extracted"
[[ -s "$WORK/custom-extracted/html/nested/source/a/a.cpp.html" ]]
"$JQ_BIN" -e '
  .summary.coverage_percent == 50 and .source_directories == ["nested/source/a"]
' "$WORK/custom-extracted/coverage.json" >/dev/null

if BUILD_WORKSPACE_DIRECTORY="$WORK/ws" "$GENERATOR" \
    --reports_file="$WORK/missing" --output_file="$WORK/bad.tar.zst" > "$WORK/error" 2>&1; then
    echo "Generator unexpectedly accepted missing reports" >&2
    exit 1
fi
grep -q 'REPORTS_FILE not found' "$WORK/error"
: > "$WORK/empty-reports"
if BUILD_WORKSPACE_DIRECTORY="$WORK/ws" "$GENERATOR" \
    --reports_file="$WORK/empty-reports" --output_file="$WORK/bad.tar.zst" > "$WORK/error" 2>&1; then
    echo "Generator unexpectedly accepted an empty report list" >&2
    exit 1
fi
grep -q 'No coverage reports found' "$WORK/error"
[[ ! -e "$WORK/bad.tar.zst" ]]
if compgen -G "$WORK/.coverage-report.*" >/dev/null; then
    echo "Generator leaked staging directories" >&2
    exit 1
fi
