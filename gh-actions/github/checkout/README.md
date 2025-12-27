# GitHub Checkout Action

A wrapper around `actions/checkout` that provides additional functionality for Envoy's CI workflows, particularly for handling ref ancestry verification in non-PR workflows.

## Purpose

This action extends the standard `actions/checkout` with two key features:

1. **Merge Commit Handling**: For PR workflows, optionally fetches and checks out the merge commit SHA (the result of merging the PR into its target branch) instead of just the HEAD commit.

2. **Ref Ancestry Verification**: For non-PR workflows where a specific ref is provided, verifies that the requested ref is an ancestor of the target branch before checking it out. This ensures that the checked-out code is based on the expected branch lineage.

## How It Works

### For PR Workflows (`pr` input is provided)

1. Fetches the PR's merge commit SHA via GitHub API (if `fetch-merge-commit` is true)
2. Checks out the merge commit
3. No ancestry verification is performed (the merge commit already represents the merged state)

### For Non-PR Workflows (`pr` input is empty)

1. If a `ref` is specified in the config:
   - Sets the `ref` as the `requested-ref` for later verification
   - Changes the checkout ref to the `branch` value
   - Ensures sufficient fetch depth (minimum `ancestor-fetch-depth`) to verify ancestry
2. Checks out the branch
3. Verifies that the `requested-ref` is an ancestor of the checked-out branch
4. If verification passes, checks out the `requested-ref`
5. If verification fails, exits with an error

This ancestry check is critical for Envoy's CI to ensure that when checking out a specific commit, it's actually part of the expected branch history and not from an unrelated branch.

## Usage

### Basic PR Checkout

```yaml
- uses: envoyproxy/toolshed/gh-actions/github/checkout@VERSION
  with:
    config: |
      repository: my-org/my-repo
    pr: ${{ github.event.pull_request.number }}
```

### Non-PR Checkout with Ref Verification

```yaml
- uses: envoyproxy/toolshed/gh-actions/github/checkout@VERSION
  with:
    config: |
      ref: abc123def456  # Specific commit to check out
    branch: main  # Branch that should contain the ref
```

This will:
1. Checkout the `main` branch
2. Verify that `abc123def456` is an ancestor of `main`
3. Checkout `abc123def456` if verification passes

### With Committer Configuration

```yaml
- uses: envoyproxy/toolshed/gh-actions/github/checkout@VERSION
  with:
    config: |
      repository: my-org/my-repo
    committer-name: "CI Bot"
    committer-email: "ci@example.com"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `config` | YAML configuration for actions/checkout. Supports all actions/checkout inputs. Special handling: 'ref' field triggers ancestor checking for non-PR workflows. | Yes | - |
| `branch` | Target branch name. Used as the base branch for checkout and ancestor verification. | No | `${{ github.ref }}` |
| `pr` | Pull request number. When provided, uses PR-specific checkout behavior. When empty, enables ref ancestry checking. | No | - |
| `ancestor-fetch-depth` | Fetch depth for checking ancestry when a specific ref is provided for non-PR workflows. | No | `20` |
| `fetch-merge-commit` | For PR workflows, whether to fetch and use the merge commit SHA. | No | `true` |
| `token` | GitHub token for authentication. | No | `${{ github.token }}` |
| `ssh-key` | SSH private key for git authentication. When provided, uses SSH instead of token auth. | No | - |
| `committer-name` | Git committer name for subsequent git operations. | No | - |
| `committer-email` | Git committer email for subsequent git operations. | No | - |
| `show-progress` | Whether to show progress status during git operations. | No | `false` |
| `strip-prefix` | Prefix to strip from the branch name in the output. | No | - |

## Outputs

| Output | Description |
|--------|-------------|
| `branch-name` | The sanitized branch name with refs/pull/ and refs/heads/ prefixes removed, and optional strip-prefix applied. |
| `merge-commit` | For PR workflows with fetch-merge-commit enabled, the SHA of the merge commit. Empty for non-PR workflows. |

## Why the Ancestry Check?

In Envoy's CI workflows, jobs may be triggered with a specific commit SHA to build/test. The ancestry check ensures that this commit is actually part of the target branch's history (e.g., `main`). This prevents accidental checkout of commits from:
- Unrelated branches
- Force-pushed or rebased history that's no longer part of the branch
- External forks with different lineage

Without this check, the CI could inadvertently build and test code that was never intended for the target branch.

## Example from Envoy

Envoy workflows typically use this action like:

```yaml
- uses: envoyproxy/toolshed/gh-actions/github/checkout@VERSION
  with:
    config: |
      ref: ${{ inputs.commit-sha }}  # Specific commit to build/test
    branch: main  # Ensure commit is from main branch
```

This ensures the commit being tested is actually part of the main branch history.
