#!/usr/bin/env bash

# Validate GCS sync inputs.
#
# WARNING: these values may be attacker-controlled - in Envoy CI they are read
# from `gcs-metadata.json` in an artefact produced by a job that ran PR code.
# They are used as the destination of
# `gcloud storage rsync --delete-unmatched-destination-objects`, so they are
# validated here (defence in depth - callers should validate too).

set -euo pipefail

BUCKET="${1:-}"
SHA="${2:-}"
REDIRECT="${3:-}"

if [[ -z "$BUCKET" ]]; then
    echo "::error::GCS bucket is empty" >&2
    exit 1
fi

if [[ ! "$BUCKET" =~ ^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$ ]]; then
    echo "::error::GCS bucket is not valid: ${BUCKET}" >&2
    exit 1
fi

if [[ ! "$SHA" =~ ^[a-f0-9]{40}$ ]]; then
    echo "::error::GCS sha is not valid: ${SHA}" >&2
    exit 1
fi

if [[ -n "$REDIRECT" ]]; then
    if [[ ! "$REDIRECT" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*(/[a-zA-Z0-9][a-zA-Z0-9_.-]*)*$ ]]; then
        echo "::error::GCS redirect is not valid: ${REDIRECT}" >&2
        exit 1
    fi
fi
