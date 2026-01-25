#!/bin/bash
# Rewrite v8 third_party includes to use external Bazel-provided deps
# Run this from the root of the v8 repository

set -e

echo "Rewriting third_party includes to use external deps..."

# fp16
find ./src ./include -type f \( -name "*.h" -o -name "*.cc" \) -exec \
    sed -i.bak 's|#include "third_party/fp16/src/include/fp16.h"|#include "fp16.h"|g' {} \;

# simdutf
find ./src ./include -type f \( -name "*.h" -o -name "*.cc" \) -exec \
    sed -i.bak 's|#include "third_party/simdutf/simdutf.h"|#include "simdutf.h"|g' {} \;

# dragonbox
find ./src ./include -type f \( -name "*.h" -o -name "*.cc" \) -exec \
    sed -i.bak 's|#include "third_party/dragonbox/src/include/dragonbox/dragonbox.h"|#include "dragonbox/dragonbox.h"|g' {} \;

# fast_float (note: this is a prefix replacement, not exact match)
find ./src ./include -type f \( -name "*.h" -o -name "*.cc" \) -exec \
    sed -i.bak 's|#include "third_party/fast_float/src/include/fast_float/|#include "fast_float/|g' {} \;

# Clean up backup files
find ./src ./include -type f -name "*.bak" -delete

echo "Unvendoring includes complete"
