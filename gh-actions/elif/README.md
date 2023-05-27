# elif GitHub Action


```yml

workflow_call:
  inputs:
    someValue:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - id: elif
      uses: envoproxy/toolshed/gh-actions/elif@VERSION
      with:
        input: "${{ inputs.someValue }}"
    - run: ./do_something.sh
      env:
        MY_VALUE: "${{ steps.elif.outputs.value }}"

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
