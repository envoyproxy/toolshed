# GitHub Checks Action

Start or update GitHub check runs in a custom CI setup.

## Usage

```yaml
- uses: envoyproxy/toolshed/actions/github/checks@VERSION
  with:
    action: start        # or 'update'
    checks: ${{ toJSON(fromJSON(steps.needs.outputs.value).checks) }}
    token: ${{ steps.appauth.outputs.token }}
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `action` | choice (`start`/`update`) | `start` | Whether to start or update check runs. |
| `checks` | JSON string | *(required)* | Map of check configurations. |
| `config` | JSON string | `{}` | Default configuration applied when starting checks. |
| `token` | string | `${{ github.token }}` | GitHub token with `checks: write` permission. |
| `text-extra` | string | *(empty)* | Additional text appended to every check's output text. |
| `retries` | number | `5` | Maximum retry attempts for transient API failures. Set to `0` to disable retries. |
| `retry-base-delay-ms` | number | `1000` | Base delay (ms) for exponential backoff between retries. |
| `retry-max-delay-ms` | number | `15000` | Maximum delay cap (ms) for a single backoff interval. |
| `fail-on-partial` | boolean | `false` | When `true`, a partial failure (some checks succeed, some fail) causes the action to fail. Default `false` allows callers to inspect the `failed` output and react accordingly. |

## Outputs

| Output | Description |
|--------|-------------|
| `checks` | JSON `{checkId: runId}` map for **successfully** created/updated check runs. |
| `failed` | JSON `{checkId: errorMessage}` map for check runs that **could not** be created/updated. Empty object (`{}`) when all checks succeed. |

## Retry behaviour

By default, transient 5xx responses and network errors (e.g. 502/503/504, `ECONNRESET`) on
`checks.create`, `checks.update`, and `checks.listForRef` are automatically retried up to 5 times
with exponential backoff + jitter, capped at 15 seconds per interval. Retry attempts are logged as
`core.warning` messages so they are visible in workflow logs.

The `@octokit/plugin-retry` plugin is also wired in at the transport layer as an additional
defence against transient failures.

## Partial failure behaviour

By default (`fail-on-partial: false`), if only *some* checks fail the action exits 0 and
`core.warning` lists the failed check IDs. Callers can inspect the `failed` output to react:

```yaml
- id: start_checks
  uses: envoyproxy/toolshed/actions/github/checks@VERSION
  with:
    action: start
    checks: ${{ inputs.checks }}
    token: ${{ steps.appauth.outputs.token }}

- if: ${{ fromJSON(steps.start_checks.outputs.failed) != '{}' }}
  run: echo "Some checks failed to start"
```

If *all* checks fail, the action always calls `core.setFailed` regardless of `fail-on-partial`.

## Development

```bash
# Run tests
npm test

# Lint
npm run lint

# Build dist/index.js (required after source changes)
npm run build
```

## License

Apache 2.
