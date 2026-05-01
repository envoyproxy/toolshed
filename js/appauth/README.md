 # appauth GitHub Action

Retreive token for Github app authentication

```yml


jobs:
  auth_example:
    runs-on: ubuntu-20.04
    steps:
    - id: auth
      uses: envoyproxy/toolshed/actions/appauth@VERSION
      with:
        key: ${{ secrets.BOT_KEY }}
        app_id: ${{ secrets.APP_ID }}

    - uses: some-action
      env:
        GITHUB_TOKEN: ${{ steps.auth.outputs.token }}


```

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `key` | | App private key (PEM format) |
| `app_id` | | GitHub App ID |
| `installation_id` | | App installation ID (optional; auto-detected if omitted) |
| `token` | | Fallback token when `key`/`app_id` are not provided |
| `token-ok` | `false` | Suppress warning when falling back to `token` |
| `retries` | `5` | Maximum retry attempts for transient errors (0 to disable) |
| `retry-base-delay-ms` | `1000` | Base delay (ms) for exponential backoff |
| `retry-max-delay-ms` | `15000` | Maximum delay (ms) for a single backoff interval |

Transient HTTP errors (408, 429, 5xx) and network errors (`ECONNRESET`, `ETIMEDOUT`, etc.) are automatically retried with exponential backoff. Each retry emits a `core.warning` line in the workflow log.

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
