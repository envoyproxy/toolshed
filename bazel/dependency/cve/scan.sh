#!/usr/bin/env bash
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
    source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
    source "$0.runfiles/$f" 2>/dev/null ||
    { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }

JQ_BIN="$(rlocation "$JQ_BIN")"
CPE_DEPS="$(rlocation "$CPE_DEPS")"
CVES_IGNORED="$(rlocation "$CVES_IGNORED")"
JQ_CVE_MATCHER="$(rlocation "$JQ_CVE_MATCHER")"
JQ_CNA_MATCHER="$(rlocation "$JQ_CNA_MATCHER")"
JQ_NVD_SCAN="$(rlocation "$JQ_NVD_SCAN")"
JQ_MERGE="$(rlocation "$JQ_MERGE")"
CVES_SOURCES="$(rlocation "$CVES_SOURCES")"
CVE_FILES="$(rlocation "$CVE_FILES")"

# NVD month files are at the root of the data directory, CVE Program
# (cvelistV5) month files under `cvelist/`.
nvd_files=()
cna_files=()
while IFS= read -r file; do
    if [[ "$file" == */cvelist/* ]]; then
        cna_files+=("$(rlocation "$file")")
    else
        nvd_files+=("$(rlocation "$file")")
    fi
done < "$CVE_FILES"

sources="$("$JQ_BIN" -r 'if type == "array" then join(" ") else tostring end' "$CVES_SOURCES")"
scan_nvd=false
scan_cna=false
for source in $sources; do
    case "$source" in
        nvd) scan_nvd=true ;;
        cna) scan_cna=true ;;
        *) echo >&2 "Unknown CVE source: $source (expected nvd or cna)"; exit 2 ;;
    esac
done
if [[ "$scan_nvd" == false && "$scan_cna" == false ]]; then
    echo >&2 "No CVE sources selected (expected nvd and/or cna)"
    exit 2
fi
if [[ "$scan_nvd" == true && ${#nvd_files[@]} -eq 0 ]]; then
    echo >&2 "No CVE data set"
    exit 1
fi
if [[ "$scan_cna" == true && ${#cna_files[@]} -eq 0 ]]; then
    echo >&2 "No CVE Program data set (cvelist/)"
    exit 1
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# One pass over the NVD data: the matches, and the ids NVD has analyzed
# (ie that have CPE configurations).
#
# `-e` fails the matchers when the data files contain no documents at all (eg
# they are empty), rather than passing an empty scan.
if [[ "$scan_nvd" == true ]]; then
    "$JQ_BIN" -e -f "$JQ_NVD_SCAN" \
        --slurpfile deps "$CPE_DEPS" --slurpfile ignored "$CVES_IGNORED" "${nvd_files[@]}" |
        "$JQ_BIN" -s '{matches: [.[].matches[]], analyzed: [.[].analyzed[]]}' \
            > "$tmpdir/nvd.json"
else
    echo '{"matches": [], "analyzed": null}' > "$tmpdir/nvd.json"
fi
if [[ "$scan_cna" == true ]]; then
    "$JQ_BIN" -e -f "$JQ_CNA_MATCHER" \
        --slurpfile deps "$CPE_DEPS" --slurpfile ignored "$CVES_IGNORED" "${cna_files[@]}" |
        "$JQ_BIN" -s '[.[][]]' > "$tmpdir/cna.json"
else
    echo '[]' > "$tmpdir/cna.json"
fi
# Union of both, tagged by source
"$JQ_BIN" -f "$JQ_MERGE" --slurpfile nvd "$tmpdir/nvd.json" "$tmpdir/cna.json"
