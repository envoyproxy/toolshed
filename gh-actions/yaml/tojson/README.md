# yaml/tojson GitHub Action

Convert Yaml to JSON

```yml


jobs:
  yaml_tojson_example:
    runs-on: ubuntu-20.04
    steps:
    - id: yaml
      uses: envoyproxy/toolshed/gh-actions/yaml/tojson@VERSION
      with:
        yaml: |
          - foo
          - bar
    - run: |
        # '["foo", "bar"]
        echo "${{ steps.yaml.outputs.json }}"


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
