#!/bin/bash
set -e

echo "Testing built binary..."

# Find the binary
BINARY="$TEST_SRCDIR/autotools_test/build_libhello/bin/hello_test"

if [ ! -f "$BINARY" ]; then
    echo "ERROR: Binary not found at $BINARY"
    exit 1
fi

# Run the binary
echo "Running hello_test..."
"$BINARY" "Bazel"

echo "Binary works!"
