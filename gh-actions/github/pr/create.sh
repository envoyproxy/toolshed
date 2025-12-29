#!/usr/bin/env bash

set -eo pipefail


SIGNOFF="$(git log -1 --pretty=%B | tail -n +2)"
PR_BODY="${PR_BODY}

${SIGNOFF}"

git checkout -b "$PR_BRANCH"
if [[ "$PR_DO_COMMIT" == "true" ]]; then
    git config --global user.name "$PR_COMMITTER_NAME"
    git config --global user.email "$PR_COMMITTER_EMAIL"
    git commit . -m "$PR_COMMIT_MESSAGE"
fi

if [[ "$PR_DRY_RUN" == "true" ]]; then
    echo "SKIPPING PR CREATE"
    exit
fi

git push --no-verify --set-upstream origin "$PR_BRANCH"
gh pr create \
  -B "$PR_BASE" \
  -H  "$PR_BRANCH" \
  --title "$PR_TITLE" \
  --body "$PR_BODY"
