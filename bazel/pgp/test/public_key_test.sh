#!/usr/bin/env bash
set -euo pipefail

"$SQ" --batch --home none --cert-store none --key-store none inspect "$PUBLIC_KEY"
