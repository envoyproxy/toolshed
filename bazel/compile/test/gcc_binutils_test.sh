#!/usr/bin/env bash
set -euo pipefail

: "${CHECK_SCRIPT:?CHECK_SCRIPT must be set}"
: "${TEST_SRCDIR:?TEST_SRCDIR must be set}"

if [[ ! -e external ]]; then
    ln -s "${TEST_SRCDIR}" external
fi

exec bash "${CHECK_SCRIPT}"
