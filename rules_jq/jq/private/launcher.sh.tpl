#!/usr/bin/env bash
# Portable across bash 3.2 (macOS /bin/bash) and newer: no arrays, no
# `${var,,}`, no `"$@"` under `set -u` when argv is empty.
set -euo pipefail
set -E

# Never fail silently: name the failing line so sandboxed runs (eg macOS
# genrules, where stderr can otherwise be lost) still explain themselves.
trap 'echo >&2 "jq launcher: command failed (exit $?) at line $LINENO: $BASH_COMMAND"' ERR
if [[ -n "${JQ_LAUNCHER_DEBUG:-}" ]]; then
  set -x
fi

# --- begin runfiles.bash initialization v3 ---
f=bazel_tools/tools/bash/runfiles/runfiles.bash
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
  source "$0.runfiles/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "$0.exe.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null ||
  { echo >&2 "ERROR: cannot find $f"; exit 1; }
# --- end runfiles.bash initialization v3 ---

# Resolve a staged module root from the runfiles key of its `.jq_root` marker.
#
# `rlocation` exits non-zero on a manifest miss; without `|| true` the
# assignment would abort the subshell under `set -e` before any diagnostic.
jq_root() {
  local marker
  marker="$(rlocation "$1" 2>/dev/null || true)"
  if [[ -n "$marker" && -e "$marker" ]]; then
    dirname "$marker"
    return
  fi
  echo >&2 "jq launcher: cannot resolve module root marker '$1'"
  exit 1
}

@@COMMAND@@
