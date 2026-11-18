#!/usr/bin/env bash

# Set the `release_date` of dependencies in YAML metadata files, in place.
#
#   release-dates.sh [--skip-unknown] <name>...   look up and fix the dates of the dependencies
#   release-dates.sh <name>=<date>...             set the given dates, with no lookup
#   release-dates.sh                              look up and fix the dates of every dependency
#
# The files are those of RELEASE_DATES_METADATA (one per line).
#
# A dependency to look up is named by its key in the dependency JSON (which is its key in the
# files), or by the `module_name` that the JSON has for it, as the two can differ. One that is in
# neither is an error, or with `--skip-unknown` is left out: not every module has metadata.
#
# The dates are looked up by the dependency checker (RELEASE_DATES_CHECK, `envoy.dependency.check`),
# which is run on the dependency JSON (RELEASE_DATES_DEPENDENCIES), and every release date
# mismatch that it reports is fixed:
#
#   ... Mismatch: <name> <current date> != <date>
#
# It makes requests to GitHub for each dependency that it checks, so for the given dependencies it
# is run on a copy of the JSON with only those in it. Checking them all is slow, and can fail on a
# rate limit or any one request: name the dependencies where they are known.
#
# Only the `release_date` line of each dependency is changed, so the rest of the file (comments,
# quoting, ordering) is left as it is. A dependency is updated in the first file that has it.

set -e -o pipefail

JQ="${JQ_BIN:-jq}"
YQ="${YQ_BIN:-yq}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

if ! command -v "$YQ" > /dev/null; then
    fail "yq binary not found: ${YQ}"
fi
# Resolve the files now: with `bazel run` they are runfiles links to the sources to change.
YAMLS=()
while IFS= read -r yaml; do
    [[ -n "$yaml" ]] || continue
    [[ -f "$yaml" ]] || fail "No such file: ${yaml}"
    YAMLS+=("$(realpath "$yaml")")
done <<< "${RELEASE_DATES_METADATA:-}"
(( ${#YAMLS[@]} > 0 )) || fail "No metadata files: set RELEASE_DATES_METADATA"

DATE_RE='[0-9]{4}-[0-9]{2}-[0-9]{2}'

# The `release_date` of a dependency in a file, or nothing if it has none there.
current_date() {
    NAME="$2" "$YQ" '.[strenv(NAME)].release_date | select(. != null)' "$1"
}

# The line of a dependency's `release_date` in a file. yq's own `line` is not used: it was a line
# out for a file that starts with a comment. Only the fields of the dependency itself are looked
# at, which are the lines with the indent of its first one: anything deeper is in a nested mapping
# or a block scalar (eg a description that mentions a `release_date:`).
date_line() {
    awk -v name="$2" '
        /^[^[:space:]#]/ {
            key = $0
            sub(/:.*$/, "", key)
            gsub(/^["\047]|["\047]$/, "", key)
            found = (key == name)
            indent = -1
            next
        }
        !found || /^[[:space:]]*(#.*)?$/ { next }
        {
            match($0, /^[[:space:]]*/)
            if (indent < 0) indent = RLENGTH
            if (RLENGTH == indent && substr($0, indent + 1) ~ /^release_date:/) { print NR; exit }
        }
    ' "$1"
}

set_date() {
    local name="$1" date="$2" yaml line current
    for yaml in "${YAMLS[@]}"; do
        current="$(current_date "$yaml" "$name")"
        [[ -n "$current" ]] || continue
        [[ "$current" =~ ^${DATE_RE}$ ]] \
            || fail "${yaml}: the release_date of ${name} is not a date: ${current}"
        line="$(date_line "$yaml" "$name")"
        [[ -n "$line" ]] || fail "${yaml}: unable to find the release_date line of ${name}"
        if [[ "$current" == "$date" ]]; then
            echo "${yaml}: ${name} is ${date}"
            return
        fi
        # Check the line holds the date that yq reads for the dependency before changing it.
        sed -n "${line}p" "$yaml" | grep -qE "^[[:space:]]+release_date:[[:space:]]*[\"']?${current}[\"']?[[:space:]]*(#.*)?$" \
            || fail "${yaml}:${line} is not the release_date of ${name}"
        sed -i -E "${line}s/(release_date:[[:space:]]*[\"']?)${current}/\\1${date}/" "$yaml"
        echo "${yaml}: ${name} ${current} -> ${date}"
        UPDATED=$((UPDATED + 1))
        return
    done
    echo "ERROR: no release_date found for ${name}" >&2
    MISSING=$((MISSING + 1))
}

declare -A APPLIED=()
UPDATED=0
MISSING=0
SEEN=0

apply() {
    local name="$1" date="$2"
    # The check reports a mismatch more than once (as it finds it, and in its summary).
    [[ "${APPLIED[$name]:-}" != "$date" ]] || return 0
    APPLIED[$name]="$date"
    SEEN=$((SEEN + 1))
    set_date "$name" "$date"
}

# Run the checker on a dependency JSON file, and print its mismatches as `<name>=<date>` lines.
check_mismatches() {
    local dependencies="$1" output rc=0 line found=0
    # `--repository_locations` is the checker's name for the dependency JSON. It fails when there
    # are mismatches, which is what is wanted from it here.
    output="$("$RELEASE_DATES_CHECK" \
                  --repository_locations="$dependencies" \
                  -c release_dates 2>&1)" || rc=$?
    # It colours its output even when that is not a terminal.
    output="$(sed -E $'s/\x1b\\[[0-9;]*[A-Za-z]//g' <<< "$output" | tr -d '\r')"
    while IFS= read -r line; do
        if [[ "$line" =~ Mismatch:[[:space:]]+([^[:space:]]+)[[:space:]]+${DATE_RE}[[:space:]]+!=[[:space:]]+(${DATE_RE})[[:space:]]*$ ]]; then
            echo "${BASH_REMATCH[1]}=${BASH_REMATCH[2]}"
            found=1
        fi
    done <<< "$output"
    if (( rc != 0 && found == 0 )); then
        echo "$output" >&2
        fail "The release date check failed (${rc}), with no mismatch to fix"
    fi
}

# The dates to set, as `<name>=<date>`, and the dependencies to look the dates up for.
UPDATES=()
LOOKUPS=()
SKIP_UNKNOWN=
ARGS=0
for arg in "$@"; do
    if [[ "$arg" == --skip-unknown ]]; then
        SKIP_UNKNOWN=1
        continue
    fi
    ARGS=$((ARGS + 1))
    if [[ "$arg" =~ ^[^[:space:]=]+=${DATE_RE}$ ]]; then
        UPDATES+=("$arg")
    elif [[ "$arg" =~ ^[^[:space:]=]+$ ]]; then
        LOOKUPS+=("$arg")
    else
        fail "Expected <name> or <name>=<date> (YYYY-MM-DD): ${arg}"
    fi
done

if (( ARGS == 0 || ${#LOOKUPS[@]} > 0 )); then
    [[ -n "${RELEASE_DATES_CHECK:-}" && -n "${RELEASE_DATES_DEPENDENCIES:-}" ]] \
        || fail "No checker and dependencies to look the release dates up with"
    dependencies="$RELEASE_DATES_DEPENDENCIES"
    if (( ARGS > 0 )); then
        command -v "$JQ" > /dev/null || fail "jq binary not found: ${JQ}"
        # The key of each: its name, or the key of the dependency with that module name.
        keys=()
        unknown=()
        for name in "${LOOKUPS[@]}"; do
            # shellcheck disable=SC2016
            key="$("$JQ" -r --arg name "$name" '
                       if has($name) then $name
                       else first(to_entries[] | select(.value.module_name? == $name) | .key) // ""
                       end' "$dependencies")"
            if [[ -n "$key" ]]; then
                keys+=("$key")
            else
                unknown+=("$name")
            fi
        done
        if (( ${#unknown[@]} > 0 )); then
            [[ -n "$SKIP_UNKNOWN" ]] || fail "Not in the dependencies: ${unknown[*]}"
            echo "Not in the dependencies, skipped: ${unknown[*]}"
        fi
        LOOKUPS=("${keys[@]}")
    fi
    if (( ${#LOOKUPS[@]} > 0 )); then
        names="$(printf '%s\n' "${LOOKUPS[@]}" | "$JQ" -R . | "$JQ" -sc .)"
        tmpdir="$(mktemp -d)"
        trap 'rm -rf "$tmpdir"' EXIT
        dependencies="${tmpdir}/dependencies.json"
        # shellcheck disable=SC2016
        "$JQ" --argjson names "$names" 'with_entries(select(.key as $key | $names | index($key)))' \
              "$RELEASE_DATES_DEPENDENCIES" > "$dependencies"
        echo "Checking the release dates of: ${LOOKUPS[*]}"
    elif (( ARGS == 0 )); then
        echo "Checking the release dates of every dependency"
    fi
    if (( ARGS == 0 || ${#LOOKUPS[@]} > 0 )); then
        found="$(check_mismatches "$dependencies")"
        while IFS= read -r update; do
            [[ -z "$update" ]] || UPDATES+=("$update")
        done <<< "$found"
    fi
fi

for update in "${UPDATES[@]}"; do
    apply "${update%%=*}" "${update#*=}"
done
for name in "${LOOKUPS[@]}"; do
    [[ -n "${APPLIED[$name]:-}" ]] || echo "${name}: no release date to fix"
done

if (( MISSING > 0 )); then
    fail "${MISSING} of ${SEEN} dependencies not found"
fi
echo "Release dates: ${UPDATED} updated, $((SEEN - UPDATED)) already set"
