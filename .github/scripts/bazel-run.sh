#!/usr/bin/env bash
# Run a bazel command inside the container and optionally collect artifacts.
#
# Required environment variables (set via workflow env: or docker compose -e):
#   BAZEL_ACTION          - bazel subcommand, e.g. "build" or "test"
#   BAZEL_ARGS            - space-separated extra flags (may be empty)
#   BAZEL_TARGETS         - space-separated target list
#   RBE_CONFIG_FLAG       - "--config=<name>" to append, or empty string
#   BES_FLAG              - "--config=bes" or empty string
#   DOWNLOAD_TOPLEVEL     - "--remote_download_toplevel" or empty string
#   REPOSITORY_CACHE_FLAG - "--repository_cache=<path>" or empty string
#   ARTIFACT_PATTERNS     - newline-separated glob patterns relative to bazel-bin
#                           (empty means skip artifact collection)
set -euo pipefail

# ---------------------------------------------------------------------------
# Build the bazel argv as an array — no eval, no word-splitting a string.
# ---------------------------------------------------------------------------
BAZEL_CMD=(bazel "${BAZEL_ACTION}")

# Append extra build flags (split on whitespace; empty string adds nothing).
# shellcheck disable=SC2206
[[ -n "${BAZEL_ARGS:-}" ]] && BAZEL_CMD+=(${BAZEL_ARGS})

# Append optional flags (each is either "--flag" or "").
[[ -n "${RBE_CONFIG_FLAG:-}" ]] && BAZEL_CMD+=("${RBE_CONFIG_FLAG}")
[[ -n "${BES_FLAG:-}"        ]] && BAZEL_CMD+=("${BES_FLAG}")
[[ -n "${DOWNLOAD_TOPLEVEL:-}" ]] && BAZEL_CMD+=("${DOWNLOAD_TOPLEVEL}")
[[ -n "${REPOSITORY_CACHE_FLAG:-}" ]] && BAZEL_CMD+=("${REPOSITORY_CACHE_FLAG}")

# Append targets (split on whitespace).
# shellcheck disable=SC2206
BAZEL_CMD+=(${BAZEL_TARGETS})

echo "Running: ${BAZEL_CMD[*]}"
"${BAZEL_CMD[@]}"

# ---------------------------------------------------------------------------
# Artifact collection — only when ARTIFACT_PATTERNS is non-empty.
# bazel-bin is a symlink into the container-local output base, which the
# host cannot follow. Resolve the real path inside the container, expand
# globs there, and copy dereferenced files into /source/dist (bind-mounted
# workspace dir) so they appear on the host after the container exits.
# ---------------------------------------------------------------------------
if [[ -n "${ARTIFACT_PATTERNS:-}" ]]; then
    BAZEL_BIN="$(readlink -f bazel-bin)"
    DIST_DIR=/source/dist

    while IFS= read -r pattern; do
        # Skip blank lines.
        [[ -z "${pattern}" ]] && continue

        dir="$(dirname "${pattern}")"
        mkdir -p "${DIST_DIR}/${dir}"

        # Expand the glob (inside the container where bazel-bin lives).
        # Use nullglob so a pattern that matches nothing produces nothing.
        # mapfile + glob expansion via eval is avoided; instead use a
        # subshell with shopt so the array assignment can use word-splitting
        # on the glob without SC2206 firing in the outer shell.
        shopt -s nullglob
        # shellcheck disable=SC2206
        files=("${BAZEL_BIN}"/${pattern})
        shopt -u nullglob

        if [[ ${#files[@]} -eq 0 ]]; then
            echo "WARNING: artifact pattern '${pattern}' matched no files in ${BAZEL_BIN}" >&2
            # Do not fail here; the host-side check will fail loudly.
            continue
        fi

        # -L dereferences symlinks so real file content lands in DIST_DIR.
        cp -L "${files[@]}" "${DIST_DIR}/${dir}/"
    done <<< "${ARTIFACT_PATTERNS}"
fi
