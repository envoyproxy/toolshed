# GitHub Release Action Test Mocks

This directory contains mock scripts for testing the github/release action.

## Mocks

### `gh`
Mocks the GitHub CLI (`gh`) command.

**Environment variables:**
- `MOCK_LOG` - Path to log file (default: `/tmp/gh-mock.log`)
- `MOCK_RELEASE_EXISTS` - Set to `true` to simulate existing release
- `MOCK_RELEASE_CREATE_FAIL` - Set to `true` to simulate create failure

**Behavior:**
- `gh release view` - Returns success if `MOCK_RELEASE_EXISTS=true`, fails otherwise
- `gh release create` - Returns mock release URL unless `MOCK_RELEASE_CREATE_FAIL=true`

### `git`
Mocks all git commands to avoid needing real repository operations.

**Environment variables:**
- `MOCK_GIT_LOG` - Path to log file (default: `/tmp/git-mock.log`)
- `MOCK_GIT_COMMIT_FAIL` - Set to `true` to simulate commit failure
- `MOCK_GIT_PUSH_FAIL` - Set to `true` to simulate push failure

**Behavior:**
- All git commands are mocked with realistic output
- Commands are logged to `MOCK_GIT_LOG`
- No actual git operations are performed

## Usage

Tests inject these mocks by:
1. Adding the mocks directory to PATH via `template-release` override
2. Setting appropriate environment variables to control mock behavior
3. Verifying mock logs in the `after` test step
