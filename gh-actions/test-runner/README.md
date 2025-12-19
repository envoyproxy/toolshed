# Test Runner

A GitHub Action for testing other GitHub Actions with fixtures and side effect validation.

## Overview

This action provides a framework for testing GitHub Actions by:
- Running setup steps (mocking commands, creating fixtures)
- Executing the action under test
- Validating outputs against expected values
- Running cleanup/verification steps

## Usage

### Basic Test

Create a test file in `gh-actions/<action-name>/tests/` with the following structure:

```yaml
using: <action-to-test>
with:
  <action-inputs>

outputs:
  <expected-outputs>
```

### Example: Testing jq action

```yaml
# gh-actions/jq/tests/basic.test.yml
using: envoyproxy/toolshed/gh-actions/jq@actions-v0.3.35
with:
  input: '{"foo": "bar", "baz": 123}'
  filter: .foo
  options: -r

outputs:
  value: bar
```

### Advanced Test with Setup and Validation

```yaml
# gh-actions/fetch/tests/with-mock.test.yml
before:
- shell: bash
  run: |
    # Create mock environment
    mkdir -p /tmp/mock/bin
    cat > /tmp/mock/bin/gh << 'EOF'
    #!/bin/bash
    echo "${@}" >> /tmp/gh-commands.log
    echo "mock output"
    EOF
    chmod +x /tmp/mock/bin/gh
    export PATH="/tmp/mock/bin:$PATH"

using: envoyproxy/toolshed/gh-actions/fetch@actions-v0.3.35
with:
  url: http://example.com/file.txt
  filename: test.txt

after:
- shell: bash
  run: |
    # Verify side effects
    if [[ ! -f /tmp/gh-commands.log ]]; then
      echo "Expected gh command was not called"
      exit 1
    fi
    # Cleanup
    rm -rf /tmp/mock /tmp/gh-commands.log

outputs:
  path: test.txt
```

## Test Configuration Schema

### Fields

- **before** (optional): Array of steps to run before the action under test
  - Used for setting up mocks, creating fixtures, etc.
  - Each step should be a valid GitHub Actions step (with `shell` and `run`, or `uses`)

- **using** (required): The action to test (e.g., `envoyproxy/toolshed/gh-actions/jq@actions-v0.3.35`)

- **with** (optional): Object containing inputs to pass to the action

- **after** (optional): Array of steps to run after the action under test
  - Used for verification, cleanup, etc.
  - Steps can fail the test by exiting with non-zero status

- **outputs** (optional): Object containing expected outputs
  - Keys are output names, values are expected values
  - If specified, actual outputs will be compared against these expected values

### Environment Variable Interpolation

Test configurations support environment variable interpolation for parameterized testing:

```yaml
# Can use environment variables in test configs
using: envoyproxy/toolshed/gh-actions/jq@${ACTION_VERSION}
with:
  input: ${TEST_INPUT}
  filter: .foo

outputs:
  value: ${EXPECTED_OUTPUT}
```

Set these variables in the workflow that runs the tests, or in a matrix strategy for multiple test variations.

## How It Works

1. **Parse Configuration**: The test-runner parses the YAML test configuration
2. **Run Before Steps**: If `before` is defined, those steps are executed
3. **Create Wrapper**: A temporary action is created that wraps the action under test
4. **Run Action**: The action under test is executed with the specified inputs
5. **Run After Steps**: If `after` is defined, those steps are executed
6. **Validate Outputs**: If `outputs` are specified, they're compared against actual outputs
7. **Cleanup**: Temporary files are removed

## CI Integration

Tests are automatically discovered and run by the `action-tests.yml` workflow:

```yaml
# .github/workflows/action-tests.yml
- Find all *.test.yml files in gh-actions/*/tests/ directories
- Run each test in a separate matrix job
- Report results
```

## Best Practices

1. **Keep tests focused**: Test one aspect of the action at a time
2. **Use descriptive names**: Name test files clearly (e.g., `filter-arrays.test.yml`, `with-options.test.yml`)
3. **Clean up**: Always clean up any resources created in `before` steps
4. **Mock external dependencies**: Use the `before` section to mock commands like `gh`, `curl`, etc.
5. **Verify side effects**: Use the `after` section to check files, logs, or other side effects
6. **Multiple tests**: Create multiple test files in the `tests/` directory for different scenarios

## Examples

See `gh-actions/*/tests/` directories for example test cases (e.g., `gh-actions/jq/tests/`, `gh-actions/test-runner/tests/`).
