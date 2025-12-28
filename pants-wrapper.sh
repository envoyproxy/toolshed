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

# Check if pants exists in ~/.local/bin (default install location)
if [ -x "$HOME/.local/bin/pants" ]; then
    exec "$HOME/.local/bin/pants" "$@"
fi

# pants is not installed, install it now
echo "Pants not found. Installing pants..." >&2

# Find the repository root (where get-pants.sh should be)
REPO_ROOT="${REPO_ROOT:-}"
if [ -z "$REPO_ROOT" ]; then
    # Try to find get-pants.sh
    if [ -f "get-pants.sh" ]; then
        REPO_ROOT="$(pwd)"
    elif [ -f "../get-pants.sh" ]; then
        REPO_ROOT="$(cd .. && pwd)"
    elif [ -f "/home/runner/work/toolshed/toolshed/get-pants.sh" ]; then
        REPO_ROOT="/home/runner/work/toolshed/toolshed"
    else
        echo "Error: Cannot find get-pants.sh. Please set REPO_ROOT or run from repository directory." >&2
        exit 1
    fi
fi

# Run get-pants.sh to install pants
if [ -f "$REPO_ROOT/get-pants.sh" ]; then
    echo "Running get-pants.sh from $REPO_ROOT..." >&2
    cd "$REPO_ROOT"
    ./get-pants.sh
    
    # Now that pants is installed, execute it
    if [ -x "$HOME/.local/bin/pants" ]; then
        exec "$HOME/.local/bin/pants" "$@"
    else
        echo "Error: pants installation failed" >&2
        exit 1
    fi
else
    echo "Error: get-pants.sh not found in $REPO_ROOT" >&2
    exit 1
fi
