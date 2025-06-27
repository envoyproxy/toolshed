#!/bin/bash
set -e

echo "Testing autotools binaries..."

# Find the external directory
RUNFILES="${TEST_SRCDIR:-$0.runfiles}"
AUTOTOOLS_DIR="$RUNFILES/autotools_x86_64"

# Test each binary
for tool in m4 autoconf automake libtool; do
    if [ -f "$AUTOTOOLS_DIR/autotools-x86_64/bin/$tool" ]; then
        echo "$tool found"
        "$AUTOTOOLS_DIR/autotools-x86_64/bin/$tool" --version | head -1
    else
        echo "ERROR: $tool not found!"
        exit 1
    fi
done

echo "All autotools binaries found and working!"
