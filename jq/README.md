# jq Test Framework

This directory contains a test framework for jq modules.

## Structure

```
jq/
├── bash.jq              # Bash/shell output helpers
├── gfm.jq               # GitHub Flavored Markdown helpers
├── github.jq            # GitHub-specific utilities
├── str.jq               # String manipulation functions
├── utils.jq             # General utilities
├── validate.jq          # Validation helpers
├── run-tests.sh         # Test runner script
└── tests/               # Test files organized by module
    ├── str/
    ├── gfm/
    └── utils/
```

## Running Tests

To run all tests:

```bash
./jq/run-tests.sh
```

The test runner will:
1. Find all `*.test.yaml` and `*.test.yml` files in `jq/tests/`
2. Execute each test
3. Display colored pass/fail results
4. Exit with status 0 if all tests pass, 1 if any fail

## Test Format

Tests are written in YAML with the following structure:

### Simple Function Test

For functions that don't require arguments or only use simple arguments:

```yaml
name: descriptive test name

input: <json value>

module: module::function

expected: <expected output>
```

**Example:**

```yaml
name: str::trim removes leading and trailing spaces

input: "  hello world  "

module: str::trim

expected: "hello world"
```

### Complex Expression Test

For functions with filter arguments or complex expressions:

```yaml
name: descriptive test name

input: <json value>

imports:
  - module1
  - module2

expression: |
  full jq expression

expected: <expected output>
```

**Example:**

```yaml
name: str::indent adds 2 spaces to each line

input: "hello\nworld"

imports:
  - str

expression: |
  str::indent(2)

expected: "  hello\n  world"
```

## Test Fields

- **name** (required): A descriptive name for the test
- **input** (required): The input data as a JSON value
- **expected** (required): The expected output as a JSON value
- **module** (optional): Module and function in `module::function` format
  - When used, the module is automatically imported
  - Cannot be used with `expression`
- **expression** (optional): A full jq expression to evaluate
  - Use this for functions with filter arguments
  - Cannot be used with `module`
- **imports** (optional): List of modules to import
  - Only needed with `expression` field
  - Automatically handled when using `module` field
- **before** (optional): A jq filter to preprocess the input (defaults to `.`)

## Writing Tests

1. Create a test file in the appropriate subdirectory:
   - `tests/str/` for string functions
   - `tests/gfm/` for GitHub Flavored Markdown functions
   - `tests/utils/` for utility functions
   - etc.

2. Name the file descriptively with `.test.yaml` extension:
   - `trim.test.yaml`
   - `blockquote.test.yaml`
   - `bytesize-mb.test.yaml`

3. Write the test following the format above

4. Run `./jq/run-tests.sh` to verify your test

## Examples

See the existing test files in `tests/` for more examples:
- Simple string functions: `tests/str/trim.test.yaml`
- Functions with arguments: `tests/str/indent.test.yaml`
- Object output: `tests/utils/version-dev.test.yaml`
- Complex functions: `tests/gfm/collapse.test.yaml`

## CI Integration

Tests are automatically run in GitHub Actions via the `.github/workflows/jq.yml` workflow on:
- Pull requests
- Pushes to main branch
- When files in `jq/` directory change
