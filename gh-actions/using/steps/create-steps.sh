#!/bin/bash -e

mkdir -p .tmp.action
output=$(printf "%s\n" "${STEPS}" \
    | sed 's/\([^\\]\)%{{ /\1${{ /g; s/^/  /')
printf "runs:\n  using: composite\n  steps:\n%s\n" "${output}" > .tmp.action/action.yml
