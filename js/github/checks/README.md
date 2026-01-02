# Retest GitHub Action

If you run GitHub Actions Workflows on your PRs, install this action to re-run failed workflow runs
for the latest commit by commenting `/retest` on your PR.

To use this bot add the following workflow to your repo at `.github/workflows/retest.yml`:

```yml
name: Retest
on:
  issue_comment:
    types: [created]

jobs:
  build:
    name: Retest
    runs-on: ubuntu-latest
    steps:
      - uses: envoproxy/toolshed/gh-actions/retest@VERSION
```

## Development

Clone this repo. Then run tests:

```bash
npm test
```

And lint:

```
npm run lint
```

# License

Apache 2.
