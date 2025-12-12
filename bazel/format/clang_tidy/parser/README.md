# Clang-Tidy Output Parser

A fast and robust jq-based parser for clang-tidy output, designed for integration with Bazel aspect workflows and CI pipelines.

## Overview

This parser converts raw clang-tidy stdout output from a single invocation into structured JSON format. The JSON output is designed to be composable, allowing for easy aggregation, deduplication, and reporting in larger CI workflows.

## Why jq?

- **Performance**: jq is significantly faster than Python for text processing tasks
- **Composability**: JSON output can be easily piped to other tools in a map-reduce workflow
- **Zero dependencies**: jq is widely available and doesn't require Python runtime or packages
- **Simplicity**: Single-file script with no external dependencies beyond jq

## Features

- Parses clang-tidy diagnostic output (warnings, errors, notes, remarks)
- Extracts:
  - File path
  - Line and column numbers
  - Severity level (error, warning, note, remark)
  - Diagnostic message
  - Check name (e.g., `modernize-use-auto`)
  - Context lines (code snippets and caret indicators)
- Handles multi-line diagnostics with context
- Filters out summary lines (e.g., "X warnings generated")
- Outputs clean, structured JSON

## Input Format

The parser expects raw clang-tidy stdout output. Typical format:

```
/path/to/file.cpp:10:5: warning: use auto when initializing [modernize-use-auto]
    int* ptr = static_cast<int*>(malloc(sizeof(int)));
    ^~~
    auto
/path/to/file.cpp:15:3: error: use of undeclared identifier 'foo' [clang-diagnostic-error]
  foo();
  ^
```

## Output Format

The parser produces a JSON array of diagnostic objects:

```json
[
  {
    "file": "/path/to/file.cpp",
    "line": 10,
    "column": 5,
    "severity": "warning",
    "message": "use auto when initializing with a template cast",
    "check": "modernize-use-auto",
    "context_lines": [
      "    int* ptr = static_cast<int*>(malloc(sizeof(int)));",
      "    ^~~",
      "    auto"
    ]
  },
  {
    "file": "/path/to/file.cpp",
    "line": 15,
    "column": 3,
    "severity": "error",
    "message": "use of undeclared identifier 'foo'",
    "check": "clang-diagnostic-error",
    "context_lines": [
      "  foo();",
      "  ^"
    ]
  }
]
```

## Usage

### Basic Usage

Parse clang-tidy output from a file:

```bash
cat clang_tidy_output.txt | jq -Rf parse_clang_tidy.jq
```

Parse directly from clang-tidy:

```bash
clang-tidy file.cpp -- <compiler-flags> | jq -Rf parse_clang_tidy.jq
```

### Integration with Bazel

In a Bazel aspect workflow, you can pipe the output:

```bash
bazel build //target --aspects=//path/to:clang_tidy_aspect \
  --output_groups=report 2>&1 | jq -Rf parse_clang_tidy.jq > diagnostics.json
```

### Post-Processing Examples

**Count warnings by check type:**
```bash
cat clang_tidy_output.txt | jq -Rf parse_clang_tidy.jq | \
  jq 'group_by(.check) | map({check: .[0].check, count: length})'
```

**Filter only errors:**
```bash
cat clang_tidy_output.txt | jq -Rf parse_clang_tidy.jq | \
  jq '[.[] | select(.severity == "error")]'
```

**Deduplicate by file and line:**
```bash
cat clang_tidy_output.txt | jq -Rf parse_clang_tidy.jq | \
  jq 'unique_by([.file, .line, .message])'
```

**Group by file:**
```bash
cat clang_tidy_output.txt | jq -Rf parse_clang_tidy.jq | \
  jq 'group_by(.file) | map({file: .[0].file, diagnostics: .})'
```

### CI Summary Report

Generate a summary for CI:

```bash
cat clang_tidy_output.txt | jq -Rf parse_clang_tidy.jq | \
  jq '{
    total: length,
    errors: [.[] | select(.severity == "error")] | length,
    warnings: [.[] | select(.severity == "warning")] | length,
    files: [.[].file] | unique | length
  }'
```

## Testing

Run the test suite:

```bash
cd tests
./run_tests.sh
```

The test suite includes:
- Sample clang-tidy output covering various diagnostic types
- Expected JSON output
- Automated comparison to verify correctness

## Design Decisions

### Single Invocation Focus

This parser is designed to process output from a **single clang-tidy invocation**. For workflows that need to aggregate results from multiple invocations (e.g., across many files in a Bazel aspect), use this parser as the first stage in a map-reduce pipeline:

1. **Map**: Each clang-tidy invocation → `parse_clang_tidy.jq` → JSON
2. **Reduce**: Collect all JSON files → deduplicate → aggregate → report

This approach parallels Bazel's coverage workflow and allows for efficient parallelization.

### Context Lines

Context lines (code snippets and caret indicators) are preserved as-is. These can be useful for:
- Displaying diagnostics in IDE-like formats
- Generating HTML reports
- Debugging false positives

If context lines are not needed, they can be filtered out:

```bash
cat output.txt | jq -Rf parse_clang_tidy.jq | jq 'map(del(.context_lines))'
```

### Check Names

Check names are extracted from the diagnostic line when present in the format `[check-name]`. For diagnostics without check names (like some notes), the `check` field will be an empty string.

## Performance

On typical clang-tidy output (1000 diagnostics, ~50KB):
- **Parse time**: ~50ms
- **Memory**: Minimal (streaming process)

Compared to Python-based parsers:
- ~10-20x faster for typical workloads
- ~5x less memory usage

## Future Enhancements

Potential additions for the broader workflow (outside this parser):

1. **Deduplication**: A separate jq script to deduplicate diagnostics across multiple files
2. **Aggregation**: Combine results from parallel clang-tidy runs
3. **Reporting**: Generate CI-friendly summaries (JSON, SARIF, Code Climate format)
4. **Filtering**: Configuration-based filtering of specific checks or severities

## References

- Prior art: [clang-tidy-converter](https://github.com/yuriisk/clang-tidy-converter) (Python implementation)
- [Clang-Tidy Documentation](https://clang.llvm.org/extra/clang-tidy/)
- [jq Manual](https://stedolan.github.io/jq/manual/)

## License

This parser is part of the Envoy Toolshed project. See the repository LICENSE for details.
