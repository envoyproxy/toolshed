#!/bin/bash -e

mkdir -p .tmp.action
__STEPS__=$(printf "%s\n" "${STEPS}" \
    | sed 's/\([^\\]\)%{{ /\1${{ /g; s/^/  /')
export __STEPS__
cat "$1" | envsubst > .tmp.action/action.yml
