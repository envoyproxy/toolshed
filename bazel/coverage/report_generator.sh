#!/usr/bin/env bash
set -euo pipefail

# --- begin runfiles.bash initialization v3 ---
f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
  source "$0.runfiles/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null ||
  { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }
# --- end runfiles.bash initialization v3 ---

fail() { echo "ERROR: $*" >&2; exit 1; }
resolve() {
    local path
    if ! path="$(rlocation "$1")" || [[ ! -f "$path" ]]; then
        fail "Runfile not found: $1"
    fi
    printf '%s\n' "$path"
}

REPORTS_FILE=
OUTPUT_FILE=
WORKSPACE_PATH="${BUILD_WORKSPACE_DIRECTORY:-}"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reports_file=*) REPORTS_FILE="${1#*=}" ;;
        --output_file=*) OUTPUT_FILE="${1#*=}" ;;
        --workspace=*) WORKSPACE_PATH="${1#*=}" ;;
        --reports_file|--output_file|--workspace)
            [[ $# -ge 2 && -n "$2" ]] || fail "Missing value for $1"
            case "$1" in
                --reports_file) REPORTS_FILE="$2" ;;
                --output_file) OUTPUT_FILE="$2" ;;
                --workspace) WORKSPACE_PATH="$2" ;;
            esac
            shift
            ;;
        *) fail "Unknown argument: $1" ;;
    esac
    shift
done
[[ -f "$REPORTS_FILE" ]] || fail "REPORTS_FILE not found: $REPORTS_FILE"
[[ -n "$OUTPUT_FILE" ]] || fail "OUTPUT_FILE is required"

SOURCE_ROOT="${SOURCE_ROOT:-source}"
SOURCE_GLOB="${SOURCE_GLOB:-*.cc}"
[[ -n "$SOURCE_ROOT" && "$SOURCE_ROOT" != /* ]] || fail "SOURCE_ROOT must be workspace-relative"
IFS=/ read -r -a root_components <<< "$SOURCE_ROOT"
for component in "${root_components[@]}"; do
    [[ -n "$component" && "$component" != . && "$component" != .. ]] ||
        fail "SOURCE_ROOT must contain only directory names"
done
if [[ -z "$WORKSPACE_PATH" ]]; then
    # Coverage invokes this in the execroot. Resolve the source-root symlink,
    # or an individual source file when the execroot contains a symlink farm.
    # Generated configs and MODULE symlinks are not reliable workspace markers.
    [[ -d "$PWD/$SOURCE_ROOT" ]] ||
        fail "Cannot locate workspace; set BUILD_WORKSPACE_DIRECTORY or pass --workspace"
    resolved_root="$(realpath "$PWD/$SOURCE_ROOT")"
    if [[ "$resolved_root" != "$PWD/$SOURCE_ROOT" ]]; then
        WORKSPACE_PATH="$resolved_root"
        for component in "${root_components[@]}"; do
            WORKSPACE_PATH="$(dirname "$WORKSPACE_PATH")"
        done
    else
        while IFS= read -r source_file; do
            resolved_source="$(realpath "$source_file")"
            source_suffix="${source_file#"$PWD/"}"
            if [[ "$resolved_source" != "$source_file" && "$resolved_source" == */"$source_suffix" ]]; then
                WORKSPACE_PATH="${resolved_source%/"$source_suffix"}"
                break
            fi
        done < <(find -L "$PWD/$SOURCE_ROOT" -type f -name "$SOURCE_GLOB" -print)
    fi
    [[ -n "$WORKSPACE_PATH" && "$WORKSPACE_PATH" != "$PWD" && "$WORKSPACE_PATH" != "$PWD/"* ]] ||
        fail "Cannot resolve source files to a real workspace; set BUILD_WORKSPACE_DIRECTORY or pass --workspace"
fi
[[ -d "$WORKSPACE_PATH" ]] || fail "Workspace not found: $WORKSPACE_PATH"
WORKSPACE_PATH="$(realpath "$WORKSPACE_PATH")"
REPORTS_FILE="$(realpath "$REPORTS_FILE")"
[[ -d "$(dirname "$OUTPUT_FILE")" ]] || fail "Output directory not found: $(dirname "$OUTPUT_FILE")"
OUTPUT_FILE="$(realpath -m "$OUTPUT_FILE")"
[[ ! -d "$OUTPUT_FILE" ]] || fail "OUTPUT_FILE is a directory: $OUTPUT_FILE"

JQ_BIN="$(resolve "${JQ_BIN:?JQ_BIN is required}")"
GRCOV="$(resolve "${GRCOV:?GRCOV is required}")"
ZSTD_BIN="$(resolve "${ZSTD_BIN:?ZSTD_BIN is required}")"
COVERAGE_CONFIG="$(resolve "${COVERAGE_CONFIG:?COVERAGE_CONFIG is required}")"
GRCOV_CONFIG="$(resolve "${GRCOV_CONFIG:?GRCOV_CONFIG is required}")"
JQ_FILTER="$(resolve "${JQ_FILTER:?JQ_FILTER is required}")"
TOOLSHED_JQ_ROOT="$(dirname "$(resolve "${TOOLSHED_JQ_ROOT:?TOOLSHED_JQ_ROOT is required}")")"
TEMPLATE_BASE="$(resolve "${TEMPLATE_BASE:?TEMPLATE_BASE is required}")"
TEMPLATE_INDEX="$(resolve "${TEMPLATE_INDEX:?TEMPLATE_INDEX is required}")"
TEMPLATE_MACROS="$(resolve "${TEMPLATE_MACROS:?TEMPLATE_MACROS is required}")"
for tool in "$JQ_BIN" "$GRCOV" "$ZSTD_BIN"; do
    [[ -x "$tool" ]] || fail "Tool is not executable: $tool"
done

# A private directory beside the destination prevents fixed-name collisions and
# leaves any pre-existing output/ or report inputs untouched.
WORK_DIR="$(dirname "$OUTPUT_FILE")/.coverage-report.${BASHPID}.${RANDOM}"
mkdir "$WORK_DIR" || fail "Cannot create report staging directory: $WORK_DIR"
trap 'rm -rf -- "$WORK_DIR"' EXIT
mkdir "$WORK_DIR/inputs" "$WORK_DIR/output"
# shellcheck disable=SC2016
"$JQ_BIN" --arg base "$TEMPLATE_BASE" --arg index "$TEMPLATE_INDEX" --arg macros "$TEMPLATE_MACROS" \
    '.templates["base.html"] = $base | .templates["index.html"] = $index | .templates["macros.html"] = $macros' \
    "$GRCOV_CONFIG" > "$WORK_DIR/grcov_config.json"

INFO_FILES=()
while IFS= read -r dat_file || [[ -n "$dat_file" ]]; do
    [[ -f "$dat_file" ]] || continue
    # grcov detects LCOV via .info; links avoid copying potentially large data.
    info_link="$WORK_DIR/inputs/${#INFO_FILES[@]}.info"
    ln -s "$(realpath "$dat_file")" "$info_link"
    INFO_FILES+=("$info_link")
done < "$REPORTS_FILE"
[[ ${#INFO_FILES[@]} -gt 0 ]] || fail "No coverage reports found in REPORTS_FILE: $REPORTS_FILE"

"$GRCOV" "${INFO_FILES[@]}" --precision 1 -s "$WORKSPACE_PATH" -t html,covdir \
    --excl-line "LCOV_EXCL_LINE" --output-config-file "$WORK_DIR/grcov_config.json" \
    -o "$WORK_DIR/output"

source_directories=
if "$JQ_BIN" -e '.directories != null' "$COVERAGE_CONFIG" >/dev/null; then
    [[ -d "$WORKSPACE_PATH/$SOURCE_ROOT" ]] || fail "Source root not found: $WORKSPACE_PATH/$SOURCE_ROOT"
    find "$WORKSPACE_PATH/$SOURCE_ROOT" -type f -name "$SOURCE_GLOB" -print > "$WORK_DIR/sources"
    while IFS= read -r source_file; do
        directory="${source_file%/*}"
        printf '%s\n' "${directory#"$WORKSPACE_PATH/"}"
    done < "$WORK_DIR/sources" | sort -u > "$WORK_DIR/directories"
    source_directories="$(cat "$WORK_DIR/directories")"
fi
"$JQ_BIN" -L "$TOOLSHED_JQ_ROOT" --slurpfile config "$COVERAGE_CONFIG" \
    --arg source_directories "$source_directories" -f "$JQ_FILTER" \
    "$WORK_DIR/output/covdir" > "$WORK_DIR/output/coverage.json"
rm -rf "$WORK_DIR/output/html/badges" "$WORK_DIR/output/html/coverage.json"
tar -cf - -C "$WORK_DIR/output" . | "$ZSTD_BIN" -c > "$WORK_DIR/report.tar.zst"
mv -f "$WORK_DIR/report.tar.zst" "$OUTPUT_FILE"
