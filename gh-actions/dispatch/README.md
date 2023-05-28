 # dispatch GitHub Action

Dispatch Github workflows using an app.

```yml


jobs:
  dispatch_example:
    runs-on: ubuntu-20.04
    steps:
    - id: dispatch
      uses: envoyproxy/toolshed/gh-actions/dispatch@VERSION
      with:
        repository: repoowner/reponame
        ref: main
        key: ${{ secrets.BOT_KEY }}
        workflow: envoy-sync.yaml
        app_id: ${{ secrets.APP_ID }}

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
