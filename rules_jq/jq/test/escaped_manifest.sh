#!/usr/bin/env bash
# Run a launcher from manifest-only runfiles whose records are all escaped, as
# Bazel writes them for keys or paths with a space, newline or backslash.
#
#   $1  rlocationpath of a jq_binary launcher with module deps
#   $2  rlocationpath of its expected output
set -euo pipefail
source "$TEST_SRCDIR/bazel_tools/tools/bash/runfiles/runfiles.bash"

launcher="$(rlocation "$1")"
expected="$(rlocation "$2")"
# Use the manifest when there is one, else list the symlink tree in its format.
manifest="${RUNFILES_MANIFEST_FILE:-}"
if [[ ! -f "$manifest" ]]; then
    manifest="$TEST_TMPDIR/listed.manifest"
    (cd "$RUNFILES_DIR" && find -L . -type f | sed 's|^\./||' | while IFS= read -r key; do
        printf '%s %s\n' "$key" "$RUNFILES_DIR/$key"
    done) > "$manifest"
fi

# Mirror every record under a directory with a space in its name, keeping the
# key layout (a module root is its marker's directory), so each path needs the
# escaped form too.
links="$TEST_TMPDIR/runfiles with space"
escaped="$TEST_TMPDIR/escaped.manifest"
: > "$escaped"
while IFS= read -r line; do
    key="${line%% *}"
    path="${line#* }"
    if [[ -n "$path" && "$path" != "$line" ]]; then
        mkdir -p "$(dirname "$links/$key")"
        ln -s "$path" "$links/$key"
        path="$links/$key"
    fi
    printf ' %s %s\n' "${key// /\\s}" "$path" >> "$escaped"
done < "$manifest"

env -u RUNFILES_DIR RUNFILES_MANIFEST_FILE="$escaped" "$launcher" > "$TEST_TMPDIR/actual"
diff -u "$expected" "$TEST_TMPDIR/actual"
