# Test Fixtures for glint

This directory contains test files and their expected outputs.

## Test Files:
- `bad.txt` - 50 lines with all types of issues (trailing whitespace, mixed indentation, no final newline)
- `bad2.txt` - 7 lines with all types of issues  
- `bad3.txt` - 7 lines with only trailing whitespace issues
- `good.txt` - Clean file with no issues

## Expected Files:
Each test file has a corresponding `.expected.json` file containing the exact JSON output that glint should produce.

To generate/update an expected file:
```bash
cargo run -- tests/fixtures/FILENAME.txt > tests/fixtures/FILENAME.txt.expected.json
```

Then manually edit to ensure paths are relative (e.g., `tests/fixtures/bad.txt` not the full path).
