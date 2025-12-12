# Clang-Tidy Parser - Usage Guide

This document provides practical examples of using the clang-tidy parser in various workflows.

## Quick Start

### Basic Usage

Parse clang-tidy output from a file:
```bash
jq -Rf parse_clang_tidy.jq < clang_tidy_output.txt
```

Or use the wrapper script:
```bash
./parse_clang_tidy.sh clang_tidy_output.txt
```

### Direct from clang-tidy

```bash
clang-tidy file.cpp -- -std=c++17 | jq -Rf parse_clang_tidy.jq
```

## Integration with Bazel Aspects

### Single Target

Run clang-tidy on a single target and parse the output:

```bash
bazel build //source:target \
  --aspects=@envoy_toolshed//format/clang_tidy:clang_tidy.bzl%clang_tidy_aspect \
  --output_groups=report \
  2>&1 | jq -Rf parse_clang_tidy.jq > diagnostics.json
```

### Multiple Targets (Map Phase)

For large codebases, run clang-tidy on multiple targets in parallel and collect JSON outputs:

```bash
#!/bin/bash
# map_clang_tidy.sh - Run clang-tidy and parse outputs for all targets

TARGETS="//source/common/... //source/server/..."
OUTPUT_DIR="clang_tidy_results"
mkdir -p "${OUTPUT_DIR}"

for target in ${TARGETS}; do
    target_name=$(echo "${target}" | tr '/:' '_')
    echo "Processing ${target}..."
    
    bazel build "${target}" \
      --aspects=@envoy_toolshed//format/clang_tidy:clang_tidy.bzl%clang_tidy_aspect \
      --output_groups=report \
      2>&1 | jq -Rf parse_clang_tidy.jq > "${OUTPUT_DIR}/${target_name}.json" &
done

wait
echo "All targets processed. Results in ${OUTPUT_DIR}/"
```

### Reduce Phase - Aggregation and Deduplication

Combine all JSON files and deduplicate:

```bash
#!/bin/bash
# reduce_clang_tidy.sh - Aggregate and deduplicate diagnostics

OUTPUT_DIR="clang_tidy_results"
FINAL_REPORT="clang_tidy_report.json"

# Combine all JSON files, deduplicate by file:line:message
jq -s '[.[][] | select(. != null)] | unique_by([.file, .line, .message])' \
  "${OUTPUT_DIR}"/*.json > "${FINAL_REPORT}"

echo "Final report: ${FINAL_REPORT}"
jq '{total: length, by_severity: group_by(.severity) | map({severity: .[0].severity, count: length})}' \
  "${FINAL_REPORT}"
```

## CI Integration Examples

### GitHub Actions

```yaml
name: Clang-Tidy

on: [pull_request]

jobs:
  clang-tidy:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq clang-tidy
      
      - name: Run clang-tidy
        run: |
          clang-tidy src/**/*.cpp -- -std=c++17 \
            | jq -Rf tools/parse_clang_tidy.jq > clang_tidy_report.json
      
      - name: Check for errors
        run: |
          ERRORS=$(jq '[.[] | select(.severity == "error")] | length' clang_tidy_report.json)
          if [ "$ERRORS" -gt 0 ]; then
            echo "Found $ERRORS errors"
            jq -r '.[] | select(.severity == "error") | "\(.file):\(.line): \(.message)"' \
              clang_tidy_report.json
            exit 1
          fi
      
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: clang-tidy-report
          path: clang_tidy_report.json
```

### GitLab CI

```yaml
clang-tidy:
  stage: test
  image: ubuntu:24.04
  before_script:
    - apt-get update && apt-get install -y jq clang-tidy
  script:
    - clang-tidy src/**/*.cpp -- -std=c++17 | jq -Rf tools/parse_clang_tidy.jq > clang_tidy_report.json
    - jq '{total: length, errors: [.[] | select(.severity == "error")] | length}' clang_tidy_report.json
  artifacts:
    reports:
      codequality: clang_tidy_report.json
    when: always
```

## Advanced Filtering and Reporting

### Filter by Check Name

Get only specific check violations:

```bash
jq -Rf parse_clang_tidy.jq < output.txt \
  | jq '[.[] | select(.check | startswith("modernize-"))]'
```

### Group by File

```bash
jq -Rf parse_clang_tidy.jq < output.txt \
  | jq 'group_by(.file) | map({
      file: .[0].file,
      total: length,
      errors: [.[] | select(.severity == "error")] | length,
      warnings: [.[] | select(.severity == "warning")] | length
    }) | sort_by(.total) | reverse'
```

### Top Issues by Check

```bash
jq -Rf parse_clang_tidy.jq < output.txt \
  | jq 'group_by(.check) | map({
      check: .[0].check,
      count: length
    }) | sort_by(.count) | reverse | .[0:10]'
```

### Generate HTML Report

Create a simple HTML report:

```bash
jq -Rf parse_clang_tidy.jq < output.txt | jq -r '
  "<html><body><h1>Clang-Tidy Report</h1>",
  "<p>Total diagnostics: \(length)</p>",
  "<table border=\"1\">",
  "<tr><th>File</th><th>Line</th><th>Severity</th><th>Message</th><th>Check</th></tr>",
  (.[] | "<tr><td>\(.file)</td><td>\(.line)</td><td>\(.severity)</td><td>\(.message)</td><td>\(.check)</td></tr>"),
  "</table></body></html>"
' > report.html
```

## Performance Tips

### Parallel Processing

For large codebases, process files in parallel:

```bash
find src -name "*.cpp" | parallel -j8 \
  "clang-tidy {} -- -std=c++17 | jq -Rf parse_clang_tidy.jq > {}.json"

# Combine results
jq -s '[.[][]]' src/**/*.cpp.json > combined_report.json
```

### Streaming for Large Outputs

For very large outputs, use streaming mode:

```bash
clang-tidy <args> | jq -Rf parse_clang_tidy.jq | jq -c '.[]' > diagnostics.ndjson
```

Then process line-by-line:

```bash
cat diagnostics.ndjson | jq -s '.' > diagnostics.json
```

## Troubleshooting

### Parser Not Finding Diagnostics

Check that your clang-tidy output matches the expected format:
```bash
clang-tidy file.cpp 2>&1 | head -20
```

Expected pattern: `file:line:col: severity: message [check]`

### Context Lines Missing

Context lines are optional. Some clang-tidy configurations may not include them. The parser will still work, just with empty `context_lines` arrays.

### Memory Issues with Large Outputs

For very large outputs (>100MB), consider splitting:

```bash
split -l 10000 large_output.txt chunk_
for chunk in chunk_*; do
  jq -Rf parse_clang_tidy.jq < "$chunk" > "${chunk}.json"
done
jq -s '[.[][]]' chunk_*.json > combined.json
```

## Related Tools

- **Bazel clang-tidy aspect**: `bazel/format/clang_tidy/clang_tidy.bzl`
- **Aggregation scripts**: (Future work - see README Future Enhancements)
- **SARIF converter**: (Future work - convert to SARIF format for IDE integration)

## Support

For issues or questions, see the main README.md or open an issue in the repository.
