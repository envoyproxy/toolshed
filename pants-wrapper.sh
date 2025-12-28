#!/usr/bin/env bash
# Pants wrapper script that auto-installs pants if not already available
#
# This wrapper is installed to /usr/local/bin/pants during Copilot setup.
# It allows users to just run "pants" without worrying about installation.
#
# How it works:
# 1. Check if pants is already installed in ~/.local/bin (default install location)
# 2. If not, automatically run get-pants.sh to install it
# 3. Then execute pants with all arguments passed through
#
# This means users can always run "pants <args>" and it will "just work"

set -euo pipefail

GET_PANTS="${GET_PANTS:-}"


run_pants () {
    if [[ -x "$HOME/.local/bin/pants" ]]; then
        exec "$HOME/.local/bin/pants" "$@"
        exit 0
    fi
}

find_get_pants () {
    if [[ -z "$GET_PANTS" ]]; then
        # Try to find get-pants.sh
        if [[ -f "get-pants.sh" ]]; then
            GET_PANTS="$(realpath ./get-pants.sh)"
        elif [[ -f "../get-pants.sh" ]]; then
            GET_PANTS="$(realpath ../get-pants.sh)"
        elif [[ -f "/home/runner/work/toolshed/toolshed/get-pants.sh" ]]; then
            GET_PANTS="/home/runner/work/toolshed/toolshed/get-pants.sh"
        else
            echo "Error: Cannot find get-pants.sh. Please set GET_PANTS or run from repository directory." >&2
            exit 1
        fi
    fi
    if [[ ! -f "$GET_PANTS" ]]; then
        echo "Error: Cannot find get-pants.sh (${GET_PANTS})." >&2
    fi
}

install_pants () {
    echo "Pants not found. Installing pants..." >&2
    find_get_pants
    echo "Running get-pants.sh from $GET_PANTS..." >&2
    "${GET_PANTS}"
}

run_pants "${@}"
install_pants
run_pants "${@}"
echo "Error: pants installation failed" >&2
exit 1
