#!/bin/bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  module-update.sh <MODULE.bazel> <deps.json> [--bazelrc=<path>] [--registry=<url>]... --report [--json-out=<path>] [--fail-on-outdated]
  module-update.sh <MODULE.bazel> <deps.json> <dep>[=<version>] [--registry=<url>] [--allow-yanked]
EOF
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

MODULE_FILE="$1"; DEP_DATA="$2"; shift 2
JQ="${JQ_BIN:-jq}"; BUILDOZER="${BUILDOZER:-}"
: "${MODULE_UPDATER_JQ_DIR:?MODULE_UPDATER_JQ_DIR must be set to the runfiles path of version.jq}"
JQ_DIR="$(dirname "${MODULE_UPDATER_JQ_DIR}")"
REPORT=0; FAIL_ON_OUTDATED=0; ALLOW_YANKED=false; JSON_OUT=""; BAZELRC="${MODULE_UPDATER_BAZELRC:-/dev/null}"; DEP=""; REQUESTED_VERSION=""; REQUESTED_REGISTRY=""
TMPDIR="$(mktemp -d)"; trap 'rm -rf "$TMPDIR"' EXIT
FETCH_METADATA_ERROR=""
: >"$TMPDIR/extra_registries"
while (($#)); do
  case "$1" in
    --report) REPORT=1 ;;
    --fail-on-outdated) FAIL_ON_OUTDATED=1 ;;
    --allow-yanked) ALLOW_YANKED=true ;;
    --json-out=*) JSON_OUT="${1#*=}" ;;
    --json-out) JSON_OUT="$2"; shift ;;
    --bazelrc=*) BAZELRC="${1#*=}" ;;
    --bazelrc) BAZELRC="$2"; shift ;;
    --registry=*) REQUESTED_REGISTRY="$(normalize_registry "${1#*=}")"; printf '%s\n' "$REQUESTED_REGISTRY" >>"$TMPDIR/extra_registries" ;;
    --registry) REQUESTED_REGISTRY="$(normalize_registry "$2")"; printf '%s\n' "$REQUESTED_REGISTRY" >>"$TMPDIR/extra_registries"; shift ;;
    --help|-h) usage; exit 0 ;;
    --*) echo "Unknown option: $1" >&2; exit 1 ;;
    *) [[ -n "$DEP" ]] && { usage >&2; exit 1; }; DEP="$1" ;;
  esac; shift
done
[[ -n "$DEP" ]] || REPORT=1
[[ "$DEP" == *=* ]] && REQUESTED_VERSION="${DEP#*=}" DEP="${DEP%%=*}"
EXTRA_JSON="$($JQ -Rsc 'split("\n") | map(select(length > 0))' <"$TMPDIR/extra_registries")"
REGISTRIES_JSON="$($JQ -Rsc --argjson extra "$EXTRA_JSON" -f "$JQ_DIR/registries.jq" <"$BAZELRC")"
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
METADATA_JSON="$($JQ -n --argjson regs "$REGISTRIES_JSON" --argjson deps "$DEPS_JSON" -f "$JQ_DIR/metadata.jq" "${files[@]}")"
REPORT_JSON="$($JQ -Sn -L "$JQ_DIR" --argjson deps "$(cat "$DEP_DATA")" --argjson registries "$REGISTRIES_JSON" --argjson metadata "$METADATA_JSON" -f "$JQ_DIR/report.jq")"
if (( REPORT == 1 )); then
  if [[ -n "$JSON_OUT" ]]; then
    printf '%s\n' "$REPORT_JSON" >"$JSON_OUT"
  else
    printf '%s\n' "$REPORT_JSON"
  fi

  if (( FAIL_ON_OUTDATED == 1 )) && $JQ -e 'any(.[]; .update_available)' <<<"$REPORT_JSON" >/dev/null; then exit 1; fi
  exit 0
fi
[[ -x "$BUILDOZER" ]] || { echo "buildozer binary not found: ${BUILDOZER}" >&2; exit 1; }
RESOLUTION="$($JQ -cn -L "$JQ_DIR" --arg dep "$DEP" --arg requested_version "$REQUESTED_VERSION" --arg requested_registry "$REQUESTED_REGISTRY" --argjson allow_yanked "$ALLOW_YANKED" --argjson report "$REPORT_JSON" -f "$JQ_DIR/resolve.jq")"
ERR="$($JQ -r '.error // empty' <<<"$RESOLUTION")"; [[ -z "$ERR" ]] || { echo "$ERR" >&2; exit 1; }
MODULE_PATH="$(resolve_module)"; grep -Eq '^[[:space:]]*module[[:space:]]*\(' "$MODULE_PATH" || { echo "Expected module() declaration in ${MODULE_PATH}" >&2; exit 1; }
TARGET="$($JQ -r '.target' <<<"$RESOLUTION")"; CURRENT="$($JQ -r '.current' <<<"$RESOLUTION")"; CHANGED=0; rc=0
if [[ "$TARGET" == "$CURRENT" ]]; then echo "${DEP}: already at ${TARGET}"; exit 0; fi

if ! "$BUILDOZER" 'print name' "${MODULE_PATH}:${DEP}" >/dev/null 2>&1; then
  echo "Dependency ${DEP} not found in ${MODULE_PATH}" >&2
  exit 1
fi

# Collect override line numbers before any edit, then apply edits bottom-up so
# that earlier rewrites cannot shift later targets.
override_lines=()
while IFS=: read -r line _; do
  [[ -n "$line" ]] || continue
  if sed -n "${line},$((line + 12))p" "$MODULE_PATH" | grep -Eq "module_name[[:space:]]*=[[:space:]]*\"${DEP}\""; then
    override_lines+=("$line")
  fi
done < <(grep -nE '^[[:space:]]*single_version_override[[:space:]]*\(' "$MODULE_PATH" || true)

for ((idx=${#override_lines[@]} - 1; idx>=0; idx--)); do
  rc=0
  run_buildozer "set version \"$TARGET\"" "${MODULE_PATH}:%${override_lines[$idx]}" || rc=$?
  if (( rc == 0 )); then
    CHANGED=1
    continue
  fi
  if (( rc != 3 )); then
    cat "$TMPDIR/buildozer.err" >&2
    exit "$rc"
  fi
done

rc=0
run_buildozer "set version \"$TARGET\"" "${MODULE_PATH}:${DEP}" || rc=$?
if (( rc == 0 )); then
  CHANGED=1
elif (( rc != 3 )); then
  cat "$TMPDIR/buildozer.err" >&2
  exit "$rc"
fi

if (( CHANGED == 0 )); then echo "${DEP}: already at ${TARGET}"; else echo "${DEP}: ${CURRENT} -> ${TARGET}"; fi
