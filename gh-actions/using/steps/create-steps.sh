#!/bin/bash -e

mkdir -p .tmp.action
if [[ "$FORMAT" == "yaml" ]]; then
    __STEPS__=$(printf "%s\n" "${STEPS}" \
        | sed 's/\([^\\]\)%{{ /\1${{ /g; s/^/  /')
    __STEPS__="
${__STEPS__}"
else
    __STEPS__=$(printf "%s\n" "${STEPS}" \
        | sed 's/\([^\\]\)%{{ /\1${{ /g')
fi
export __STEPS__
envsubst < "$1" > .tmp.action/action.yml
