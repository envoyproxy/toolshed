# jq Modules

This directory contains reusable jq modules for data processing and command-line argument parsing.

## Modules

### args.jq

Parse command-line arguments with type support.

#### Features

- **Typed Arguments**: Support for `string`, `int`, `bool`, and `array` types
- **Backward Compatible**: Supports legacy array-based config format
- **Strict Validation**: Errors on repeated non-array arguments
- **Flexible Syntax**: Supports `--key=value`, `--key value`, `-k value` formats

#### Usage

```jq
import "args" as args;

# Basic usage with old array format (backward compatible)
args::parse({"flags": ["verbose"], "options": ["output"]})

# New typed format
args::parse({
  "flags": {"verbose": "bool", "level": "int"},
  "options": {"name": "string", "count": "int", "items": "array"}
})
```

#### Type System

- **`string`** (default): No conversion, returns string value
- **`int`**: Converts value to number using `tonumber`
- **`bool`**: Converts "true", "1", "yes" to `true`, others to `false` (case-insensitive)
- **`array`**: Always returns an array, even with single value. Allows repeated arguments.

#### Examples

```bash
# String type (default)
echo '"--name=John"' | jq 'import "args" as args; args::parse({"options": {"name": "string"}})'
# Output: {"args": [], "flags": {}, "options": {"name": "John"}}

# Int type
echo '"--port=8080"' | jq 'import "args" as args; args::parse({"options": {"port": "int"}})'
# Output: {"args": [], "flags": {}, "options": {"port": 8080}}

# Bool type
echo '"--enabled=yes"' | jq 'import "args" as args; args::parse({"options": {"enabled": "bool"}})'
# Output: {"args": [], "flags": {}, "options": {"enabled": true}}

# Array type (allows repeated args)
echo '"--tag v1 --tag v2"' | jq 'import "args" as args; args::parse({"options": {"tag": "array"}})'
# Output: {"args": [], "flags": {}, "options": {"tag": ["v1", "v2"]}}

# Comprehensive example
echo '"--name=App --port=8080 --debug --workers=4 --tags v1 --tags v2 input.conf"' | \
  jq 'import "args" as args; args::parse({
    "flags": {"debug": "bool"},
    "options": {"name": "string", "port": "int", "workers": "int", "tags": "array"}
  })'
# Output: {
#   "args": ["input.conf"],
#   "flags": {"debug": true},
#   "options": {
#     "name": "App",
#     "port": 8080,
#     "workers": 4,
#     "tags": ["v1", "v2"]
#   }
# }
```

#### Error Handling

The parser will error if you try to repeat an argument that is not configured as an array type:

```bash
# This will error
echo '"--name=John --name=Jane"' | jq 'import "args" as args; args::parse({"options": {"name": "string"}})'
# Error: Option '--name' specified multiple times but is not configured as array type

# This works
echo '"--name=John --name=Jane"' | jq 'import "args" as args; args::parse({"options": {"name": "array"}})'
# Output: {"args": [], "flags": {}, "options": {"name": ["John", "Jane"]}}
```

## Testing

Run all tests:

```bash
./run-tests.sh
```

Tests are located in `tests/` and use YAML format. See existing tests for examples.
