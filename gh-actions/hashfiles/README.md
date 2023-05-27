# hashfiles GitHub Action

Create a hash of files with a more flexible input format than the
Github `hashFiles` function.

Default is to error if no hash is created.

```yml

workflow_call:
  inputs:
    somePath:
    files:
      default: |
        file1.txt
        **/*.xyz

jobs:
  build:
    id: hashed
    runs-on: ubuntu-latest
    steps:
    - id: hashed
      uses: envoproxy/toolshed/gh-actions/hashfiles@VERSION
      with:
        files: ${input.files}
    - name: Cache something
      uses: actions/cache@v3
      with:
        key: "${{ steps.hashed.outputs.value }}"
        path: "${{ inputs.somePath }}"

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
