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

# Runfiles, resolved here rather than by sourcing `runfiles.bash`: every key
# this launcher looks up is already a canonical `<repo>/<path>`, so it needs no
# repo mapping, and keeping it self-contained keeps it on bash 3.2.
#
# As in `runfiles.bash`, `$0`'s runfiles are only used when neither
# RUNFILES_DIR nor RUNFILES_MANIFEST_FILE names one.
if [[ ! -d "${RUNFILES_DIR:-/dev/null}" && ! -f "${RUNFILES_MANIFEST_FILE:-/dev/null}" ]]; then
  if [[ -f "$0.runfiles_manifest" ]]; then
    RUNFILES_MANIFEST_FILE="$0.runfiles_manifest"
  elif [[ -f "$0.runfiles/MANIFEST" ]]; then
    RUNFILES_MANIFEST_FILE="$0.runfiles/MANIFEST"
  elif [[ -d "$0.runfiles" ]]; then
    RUNFILES_DIR="$0.runfiles"
  fi
fi
runfiles_dir="${RUNFILES_DIR:-}"
runfiles_manifest="${RUNFILES_MANIFEST_FILE:-}"
if [[ -z "$runfiles_manifest" && -n "$runfiles_dir" ]]; then
  if [[ -f "$runfiles_dir/MANIFEST" ]]; then
    runfiles_manifest="$runfiles_dir/MANIFEST"
  elif [[ -f "${runfiles_dir}_manifest" ]]; then
    runfiles_manifest="${runfiles_dir}_manifest"
  fi
fi

# Print the path for a runfiles key, from the symlink tree when it has the
# entry, else from the manifest. Prints nothing and fails on a miss.
rlocation() {
  if [[ -n "$runfiles_dir" && -e "$runfiles_dir/$1" ]]; then
    echo "$runfiles_dir/$1"
    return 0
  fi
  if [[ -n "$runfiles_manifest" && -f "$runfiles_manifest" ]]; then
    local path
    # A record starting with a space is escaped (a key or path with a space,
    # newline or backslash): `\s`, `\n` and `\b` stand for those characters.
    path="$(RLOCATION_KEY="$1" awk '
      function unescape(s,    out, i, c, n) {
        out = ""
        for (i = 1; i <= length(s); i++) {
          c = substr(s, i, 1)
          n = substr(s, i + 1, 1)
          if (c == "\\" && (n == "s" || n == "n" || n == "b")) {
            out = out (n == "s" ? " " : n == "n" ? "\n" : "\\")
            i++
          } else {
            out = out c
          }
        }
        return out
      }
      BEGIN { key = ENVIRON["RLOCATION_KEY"] }
      substr($0, 1, 1) == " " {
        record = substr($0, 2)
        split_at = index(record, " ")
        if (split_at && unescape(substr(record, 1, split_at - 1)) == key) {
          print unescape(substr(record, split_at + 1))
          exit
        }
        next
      }
      index($0, key " ") == 1 { print substr($0, length(key) + 2); exit }
    ' "$runfiles_manifest")"
    if [[ -n "$path" ]]; then
      echo "$path"
      return 0
    fi
  fi
  return 1
}

# Resolve a staged module root from the runfiles key of its `.jq_root` marker.
#
# `rlocation` fails on a miss; without `|| true` the assignment would abort the
# subshell under `set -e` before any diagnostic.
jq_root() {
  local marker
  marker="$(rlocation "$1" || true)"
  if [[ -n "$marker" && -e "$marker" ]]; then
    dirname "$marker"
    return
  fi
  echo >&2 "jq launcher: cannot resolve module root marker '$1'"
  exit 1
}

@@COMMAND@@
