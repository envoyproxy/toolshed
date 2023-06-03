 # appauth GitHub Action

Retreive token for Github app authentication

```yml


jobs:
  auth_example:
    runs-on: ubuntu-20.04
    steps:
    - id: auth
      uses: envoyproxy/toolshed/gh-actions/appauth@VERSION
      with:
        key: ${{ secrets.BOT_KEY }}
        app_id: ${{ secrets.APP_ID }}

    - uses: some-action
      env:
        GITHUB_TOKEN: ${{ steps.auth.outputs.value }}


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
