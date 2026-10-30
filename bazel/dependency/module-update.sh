#!/bin/bash
set -euo pipefail

usage() {
  cat <<'EOF_USAGE'
Usage:
  module-update.sh <MODULE.bazel> <deps.json> [--bazelrc=<path>] [--registry=<url>]... --report [--format=json|markdown] [--json-out=<path>] [--markdown-out=<path>] [--fail-on-outdated] [--fail-on-outdated-dev]
  module-update.sh <MODULE.bazel> <deps.json> <dep>[=<version>]... [--registry=<url>] [--allow-yanked]
  module-update.sh <MODULE.bazel> <deps.json> --outdated[=<registry-match>] [--registry=<url>] [--allow-yanked]

Several <dep>[=<version>] arguments are resolved from a single registry scan and applied together;
nothing is edited unless every one of them resolves. --outdated updates every dependency with a
newer version on its current registry, optionally only those whose current registry contains
<registry-match>.
EOF_USAGE
}

normalize_registry() {
  printf '%s/\n' "${1%/}"
}

fetch_metadata() {
  local registry="$1"
  local dep="$2"
  local out="$3"
  local rel="modules/${dep}/metadata.json"
  local status
  local url

  FETCH_METADATA_ERROR=""

  if [[ "$registry" == file://* ]]; then
    cp "${registry#file://}/$rel" "$out" 2>/dev/null || return 1
    return 0
  fi

  if [[ "$registry" != *://* ]]; then
    cp "${registry%/}/$rel" "$out" 2>/dev/null || return 1
    return 0
  fi

  url="${registry}${rel}"
  if ! status="$("${CURL_BIN:-curl}" -sSL -o "$out" -w '%{http_code}' "$url")"; then
    FETCH_METADATA_ERROR="Failed to fetch ${url}"
    rm -f "$out"
    return 2
  fi

  if [[ "$status" == "404" ]]; then
    rm -f "$out"
    return 1
  fi

  if [[ ! "$status" =~ ^2 ]]; then
    FETCH_METADATA_ERROR="Unexpected status ${status} fetching ${url}"
    rm -f "$out"
    return 2
  fi

  return 0
}

resolve_module() {
  if [[ -z "${BUILD_WORKSPACE_DIRECTORY:-}" ]]; then
    printf '%s\n' "$MODULE_FILE"
    return
  fi

  (
    cd "$BUILD_WORKSPACE_DIRECTORY"
    realpath "$MODULE_FILE"
  )
}

run_buildozer() {
  local cmd="$1"
  local label="$2"
  local err="$TMPDIR/buildozer.err"
  local rc

  set +e
  "$BUILDOZER" "$cmd" "$label" >/dev/null 2>"$err"
  rc=$?
  set -e

  return "$rc"
}

# Print the `module_name` attribute of the rule starting at the given line, or
# nothing if buildozer cannot read it.
override_module_name() {
  local label="$1"
  local name

  set +e
  name="$("$BUILDOZER" 'print module_name' "$label" 2>/dev/null)"
  set -e

  printf '%s\n' "$name"
}

# Report a failed buildozer edit and restore MODULE_PATH, so earlier edits in the same run are
# not left half-applied.
fail_update() {
  cat "$TMPDIR/buildozer.err" >&2
  cat "$TMPDIR/MODULE.bazel.orig" > "$MODULE_PATH"
  echo "Update failed, ${MODULE_PATH} restored" >&2
  exit "$1"
}

# Rewrite the `bazel_dep(name = "<dep>")` version, and any
# `single_version_override(module_name = "<dep>")`, in MODULE_PATH.
apply_update() {
  local dep="$1"
  local target="$2"
  local current="$3"
  local changed=0
  local rc
  local line
  local module_name
  local idx
  local -a override_lines=()

  if [[ "$target" == "$current" ]]; then
    echo "${dep}: already at ${target}"
    return 0
  fi

  # Collect `single_version_override(module_name = "<dep>")` rules. Each candidate
  # is read structurally via buildozer so comments and neighbouring rules are never
  # matched; the comparison is exact so prefix-sharing module names don't collide.
  while IFS=: read -r line _; do
    [[ -n "$line" ]] || continue
    module_name="$(override_module_name "${MODULE_PATH}:%${line}")"
    if [[ -z "$module_name" ]]; then
      echo "WARNING: unable to read module_name of single_version_override at ${MODULE_PATH}:${line}, skipping" >&2
      continue
    fi
    if [[ "$module_name" == "$dep" ]]; then
      override_lines+=("$line")
    fi
  done < <(grep -nE '^[[:space:]]*single_version_override[[:space:]]*\(' "$MODULE_PATH" || true)

  for ((idx=${#override_lines[@]} - 1; idx>=0; idx--)); do
    rc=0
    run_buildozer "set version \"$target\"" "${MODULE_PATH}:%${override_lines[$idx]}" || rc=$?
    if (( rc == 0 )); then
      changed=1
      continue
    fi
    if (( rc != 3 )); then
      fail_update "$rc"
    fi
  done

  rc=0
  run_buildozer "set version \"$target\"" "${MODULE_PATH}:${dep}" || rc=$?
  if (( rc == 0 )); then
    changed=1
  elif (( rc != 3 )); then
    fail_update "$rc"
  fi

  if (( changed == 0 )); then
    echo "${dep}: already at ${target}"
  else
    echo "${dep}: ${current} -> ${target}"
  fi
}

MODULE_FILE="$1"
DEP_DATA="$2"
shift 2
JQ="${JQ_BIN:-jq}"
BUILDOZER="${BUILDOZER:-}"
: "${TOOLSHED_JQ_ROOT:?TOOLSHED_JQ_ROOT must be set to the runfiles path of modules_root.marker}"
JQ_DIR="$(dirname "$TOOLSHED_JQ_ROOT")"
REPORT=0
FAIL_ON_OUTDATED=0
FAIL_ON_OUTDATED_DEV=0
ALLOW_YANKED=false
FORMAT=json
JSON_OUT=""
MARKDOWN_OUT=""
BAZELRC="${MODULE_UPDATER_BAZELRC:-/dev/null}"
DEP_ARGS=()
OUTDATED=0
OUTDATED_MATCH=""
REQUESTED_REGISTRY=""
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
FETCH_METADATA_ERROR=""
: >"$TMPDIR/extra_registries"
while (($#)); do
  case "$1" in
    --report) REPORT=1 ;;
    --fail-on-outdated) FAIL_ON_OUTDATED=1 ;;
    --fail-on-outdated-dev) FAIL_ON_OUTDATED_DEV=1 ;;
    --allow-yanked) ALLOW_YANKED=true ;;
    --outdated) OUTDATED=1 ;;
    --outdated=*) OUTDATED=1; OUTDATED_MATCH="${1#*=}" ;;
    --format=*) FORMAT="${1#*=}" ;;
    --format) FORMAT="$2"; shift ;;
    --json-out=*) JSON_OUT="${1#*=}" ;;
    --json-out) JSON_OUT="$2"; shift ;;
    --markdown-out=*) MARKDOWN_OUT="${1#*=}" ;;
    --markdown-out) MARKDOWN_OUT="$2"; shift ;;
    --bazelrc=*) BAZELRC="${1#*=}" ;;
    --bazelrc) BAZELRC="$2"; shift ;;
    --registry=*)
      REQUESTED_REGISTRY="$(normalize_registry "${1#*=}")"
      printf '%s\n' "$REQUESTED_REGISTRY" >>"$TMPDIR/extra_registries"
      ;;
    --registry)
      REQUESTED_REGISTRY="$(normalize_registry "$2")"
      printf '%s\n' "$REQUESTED_REGISTRY" >>"$TMPDIR/extra_registries"
      shift
      ;;
    --help|-h) usage; exit 0 ;;
    --*) echo "Unknown option: $1" >&2; exit 1 ;;
    *) DEP_ARGS+=("$1") ;;
  esac
  shift
done
if (( OUTDATED == 1 )) && (( ${#DEP_ARGS[@]} > 0 )); then
  echo "--outdated cannot be combined with dependency arguments" >&2
  usage >&2
  exit 1
fi
if (( OUTDATED == 1 )) && (( REPORT == 1 )); then
  echo "--outdated cannot be combined with --report" >&2
  exit 1
fi
(( ${#DEP_ARGS[@]} > 0 || OUTDATED == 1 )) || REPORT=1
case "$FORMAT" in
  json|markdown) ;;
  *) echo "Unknown format: $FORMAT" >&2; exit 1 ;;
esac
EXTRA_JSON="$($JQ -Rsc 'split("\n") | map(select(length > 0))' <"$TMPDIR/extra_registries")"
REGISTRIES_JSON="$($JQ -Rsc -L "$JQ_DIR" --argjson extra "$EXTRA_JSON" 'import "bazel/dep" as dep; dep::registries_from_args' <"$BAZELRC")"
[[ "$REGISTRIES_JSON" != '[]' ]] || { echo "No registries configured. Pass --bazelrc or --registry." >&2; exit 1; }
DEPS_JSON="$($JQ -rc 'to_entries | map(select(.value.version | type == "string") | .key)' "$DEP_DATA")"
registries=()
while IFS= read -r registry; do
  [[ -n "$registry" ]] && registries+=("$registry")
done < <($JQ -r '.[]' <<<"$REGISTRIES_JSON")
deps=()
while IFS= read -r dep; do
  [[ -n "$dep" ]] && deps+=("$dep")
done < <($JQ -r '.[]' <<<"$DEPS_JSON")
idx=0
for registry in "${registries[@]}"; do
  mkdir -p "$TMPDIR/$idx"
  for dep in "${deps[@]}"; do
    if fetch_metadata "$registry" "$dep" "$TMPDIR/$idx/$dep.json"; then
      continue
    else
      rc=$?
    fi
    if (( rc == 1 )); then
      continue
    fi

    if (( rc == 2 )); then
      echo "$FETCH_METADATA_ERROR" >&2
      exit 1
    fi

    echo "Unexpected metadata fetch result ${rc} for ${registry}modules/${dep}/metadata.json" >&2
    exit 1
  done
  idx=$((idx + 1))
done
find "$TMPDIR" -path '*/[0-9]*/*.json' | sort >"$TMPDIR/files"
files=()
if [[ -s "$TMPDIR/files" ]]; then
  while IFS= read -r file; do
    [[ -n "$file" ]] && files+=("$file")
  done <"$TMPDIR/files"
fi
METADATA_JSON="$($JQ -n -L "$JQ_DIR" --argjson regs "$REGISTRIES_JSON" --argjson deps "$DEPS_JSON" 'import "bazel/dep" as dep; dep::metadata_versions_from_args' "${files[@]}")"
REPORT_JSON="$($JQ -n -L "$JQ_DIR" --argjson deps "$(cat "$DEP_DATA")" --argjson registries "$REGISTRIES_JSON" --argjson metadata "$METADATA_JSON" 'import "bazel/dep" as dep; dep::report_from_args')"
if (( REPORT == 1 )); then
  if [[ -n "$JSON_OUT" ]]; then
    printf '%s\n' "$REPORT_JSON" >"$JSON_OUT"
  fi
  REPORT_MD=""
  if [[ -n "$MARKDOWN_OUT" || "$FORMAT" == markdown ]]; then
    REPORT_MD="$($JQ -r -L "$JQ_DIR" 'import "bazel/dep" as dep; dep::report_markdown' <<<"$REPORT_JSON")"
    if [[ -n "$MARKDOWN_OUT" ]]; then
      printf '%s\n' "$REPORT_MD" >"$MARKDOWN_OUT"
    fi
  fi
  if [[ "$FORMAT" == markdown ]]; then
    printf '%s\n' "$REPORT_MD"
  elif [[ -z "$JSON_OUT" ]]; then
    printf '%s\n' "$REPORT_JSON"
  fi

  if (( FAIL_ON_OUTDATED == 1 )) && $JQ -e 'any(.[]; .update_available == true and ((.dev_dependency // false) | not))' <<<"$REPORT_JSON" >/dev/null; then
    exit 1
  fi
  if (( FAIL_ON_OUTDATED_DEV == 1 )) && $JQ -e 'any(.[]; .update_available == true and (.dev_dependency // false))' <<<"$REPORT_JSON" >/dev/null; then
    exit 1
  fi
  exit 0
fi
[[ -x "$BUILDOZER" ]] || { echo "buildozer binary not found: ${BUILDOZER}" >&2; exit 1; }
if (( OUTDATED == 1 )); then
  # shellcheck disable=SC2016  # `$match` is a jq variable, not a shell expansion
  OUTDATED_FILTER='
    to_entries[]
    | select(.value.update_available == true
             and (($match == "") or ((.value.current_registry // "") | contains($match))))
    | .key'
  DEP_ARGS=()
  while IFS= read -r dep; do
    [[ -n "$dep" ]] && DEP_ARGS+=("$dep")
  done < <($JQ -r --arg match "$OUTDATED_MATCH" "$OUTDATED_FILTER" <<<"$REPORT_JSON")
  if (( ${#DEP_ARGS[@]} == 0 )); then
    echo "No outdated dependencies${OUTDATED_MATCH:+ on registries matching ${OUTDATED_MATCH}}"
    exit 0
  fi
fi
MODULE_PATH="$(resolve_module)"
grep -Eq '^[[:space:]]*module[[:space:]]*\(' "$MODULE_PATH" || { echo "Expected module() declaration in ${MODULE_PATH}" >&2; exit 1; }

# Resolve (and check for) every requested dependency before editing anything, so a bad
# request leaves MODULE.bazel untouched.
# Read the declared `bazel_dep` names once. A failure here (eg MODULE.bazel does not parse) is
# fatal, rather than being mistaken for an undeclared dependency. Exit code 3 means there are no
# `bazel_dep` rules (as in `module_deps_json`).
declared_status=0
DECLARED_DEPS="$("$BUILDOZER" 'print name' "${MODULE_PATH}:%bazel_dep" 2>"$TMPDIR/declared.err")" \
  || declared_status=$?
if (( declared_status == 3 )); then
  DECLARED_DEPS=""
elif (( declared_status != 0 )); then
  cat "$TMPDIR/declared.err" >&2
  echo "Unable to read bazel_dep declarations from ${MODULE_PATH}" >&2
  exit 1
fi

dep_names=()
dep_targets=()
dep_currents=()
requested_deps=()
for dep_arg in "${DEP_ARGS[@]}"; do
  dep="$dep_arg"
  requested_version=""
  [[ "$dep_arg" == *=* ]] && requested_version="${dep_arg#*=}" dep="${dep_arg%%=*}"
  # Each request is resolved against the original versions, so a repeated dependency would be
  # compared against a stale current version once an earlier request had updated it.
  for seen in "${requested_deps[@]+"${requested_deps[@]}"}"; do
    if [[ "$seen" == "$dep" ]]; then
      echo "Dependency ${dep} requested more than once" >&2
      exit 1
    fi
  done
  requested_deps+=("$dep")
  # Check the declaration before resolving, so an undeclared `--outdated` entry is skipped even if
  # the selected registry cannot resolve it.
  if ! grep -qxF -- "$dep" <<<"$DECLARED_DEPS"; then
    if (( OUTDATED == 1 )); then
      # The dependency data may cover more than this MODULE.bazel declares.
      echo "WARNING: ${dep} not declared in ${MODULE_PATH}, skipping" >&2
      continue
    fi
    echo "Dependency ${dep} not found in ${MODULE_PATH}" >&2
    exit 1
  fi
  RESOLUTION="$($JQ -n -L "$JQ_DIR" --arg dep "$dep" --arg requested_version "$requested_version" --arg requested_registry "$REQUESTED_REGISTRY" --argjson allow_yanked "$ALLOW_YANKED" --argjson report "$REPORT_JSON" 'import "bazel/dep" as dep; dep::resolve_from_args')"
  ERR="$($JQ -r '.error // empty' <<<"$RESOLUTION")"
  [[ -z "$ERR" ]] || { echo "$ERR" >&2; exit 1; }
  dep_names+=("$dep")
  dep_targets+=("$($JQ -r '.target' <<<"$RESOLUTION")")
  dep_currents+=("$($JQ -r '.current' <<<"$RESOLUTION")")
done

if (( ${#dep_names[@]} == 0 )); then
  echo "No outdated dependencies declared in ${MODULE_PATH}"
  exit 0
fi

cp "$MODULE_PATH" "$TMPDIR/MODULE.bazel.orig"
for ((i=0; i<${#dep_names[@]}; i++)); do
  apply_update "${dep_names[$i]}" "${dep_targets[$i]}" "${dep_currents[$i]}"
done
