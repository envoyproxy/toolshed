#!/bin/bash
# Checks that @cert_epoch//:year holds a four digit year.
set -euo pipefail

year="$(tr -d '[:space:]' < "$1")"
if [[ ! "$year" =~ ^[0-9]{4}$ ]]; then
    echo "FAIL: expected a four digit year, got '${year}'" >&2
    exit 1
fi
echo "PASS: certificate epoch year ${year}"
