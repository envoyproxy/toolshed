#!/usr/bin/env bash

set -e -o pipefail


OUTPUT='{"workflow_runs": []}'
# shellcheck disable=SC2016
JQ_CHECK='
    ($names | split(",") | map(gsub("^\"|\"$"; "") | gsub("^ +| +$"; ""))) as $required
    | [.workflow_runs[].name] as $actual
    | ($required - $actual)
    | length == 0'

for PAGE in $(seq 1 "${MAX_PAGES}"); do
    PAGE_OUTPUT=$(gh api --jq "${SCRIPT_JQ}" "/repos/${REPO}/actions/runs?page=${PAGE}&head_sha=${HEAD_SHA}&per_page=${PER_PAGE}")
    OUTPUT=$(echo "$OUTPUT" | jq -c --argjson page "$PAGE_OUTPUT" '{workflow_runs: (.workflow_runs + $page.workflow_runs)}')
    if echo "$OUTPUT" | jq -e --arg names "$WF_NAMES" "$JQ_CHECK" > /dev/null; then
        break
    fi
done
echo "$OUTPUT"
