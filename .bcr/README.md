# Publishing envoy_toolshed to Bazel Central Registry (BCR)

This document describes the workflow for publishing the `envoy_toolshed` Bazel module to the [Bazel Central Registry (BCR)](https://github.com/bazelbuild/bazel-central-registry).

## Overview

The toolshed repository uses the [publish-to-bcr](https://github.com/bazel-contrib/publish-to-bcr) GitHub Action to automate publishing releases to the BCR. When a release is created with a tag following the pattern `bazel-v*`, the workflow automatically:

1. Creates a BCR entry from the `.bcr` templates
2. Generates attestations for the release artifacts
3. Pushes the entry to a fork of the BCR
4. Opens a pull request against the upstream BCR

## Prerequisites

### 1. Fork the Bazel Central Registry

Create a fork of [bazelbuild/bazel-central-registry](https://github.com/bazelbuild/bazel-central-registry) in the `envoyproxy` organization:

1. Navigate to https://github.com/bazelbuild/bazel-central-registry
2. Click "Fork" in the top-right corner
3. Select the `envoyproxy` organization as the destination
4. This creates `envoyproxy/bazel-central-registry`

**Note:** The fork must exist at `envoyproxy/bazel-central-registry` as specified in the workflow configuration.

### 2. Create a Personal Access Token (PAT)

Create a Classic Personal Access Token with the following permissions:

1. Go to https://github.com/settings/tokens (GitHub Settings > Developer settings > Personal access tokens > Tokens (classic))
2. Click "Generate new token (classic)"
3. Give it a descriptive name like "BCR Publish Token for envoyproxy/toolshed"
4. Set an appropriate expiration date (or no expiration for automation)
5. Select the following scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
6. Click "Generate token" and **copy the token immediately** (you won't be able to see it again)

**Why these permissions?**
- `repo`: Required to push commits to the BCR fork
- `workflow`: Required to open pull requests against the BCR

> [!NOTE]
> Fine-grained Personal Access Tokens (PATs) are not fully supported because they cannot open pull requests against public repositories. If this limitation is resolved in the future, fine-grained PATs may become an option. For now, use Classic PATs.

### 3. Add the Token as a Repository Secret

Add the PAT as a secret in the toolshed repository:

1. Go to https://github.com/envoyproxy/toolshed/settings/secrets/actions
2. Click "New repository secret"
3. Name: `BCR_PUBLISH_TOKEN`
4. Value: Paste the token you copied in step 2
5. Click "Add secret"

The workflow is now configured to use this token via `${{ secrets.BCR_PUBLISH_TOKEN }}`.

## Publishing a Release

### Automatic Publishing

When you create a GitHub Release with a tag that matches the pattern `bazel-v*`, the publish workflow will automatically run:

1. **Create a release** via the GitHub UI or CLI:
   ```bash
   # Tag the release
   git tag bazel-v0.3.11
   git push origin bazel-v0.3.11

   # Create the GitHub release
   gh release create bazel-v0.3.11 --title "Bazel Module v0.3.11" --notes "Release notes here"
   ```

2. **Monitor the workflow**:
   - Go to https://github.com/envoyproxy/toolshed/actions/workflows/publish-to-bcr.yml
   - The workflow will create a BCR entry and open a PR

3. **Review the pull request**:
   - The workflow opens a **draft PR** by default
   - Review the PR at https://github.com/bazelbuild/bazel-central-registry/pulls
   - If everything looks good, mark the PR as "Ready for review"
   - BCR maintainers will review and merge the PR

### Manual Publishing

If you need to republish a release (e.g., after fixing templates), you can manually trigger the workflow:

1. Go to https://github.com/envoyproxy/toolshed/actions/workflows/publish-to-bcr.yml
2. Click "Run workflow"
3. Enter the tag name (e.g., `bazel-v0.3.11`)
4. Click "Run workflow"

### Tag Naming Convention

- **Pattern**: `bazel-v{VERSION}`
- **Examples**:
  - ✅ `bazel-v0.3.11` → publishes version `0.3.11`
  - ✅ `bazel-v1.0.0` → publishes version `1.0.0`
  - ❌ `v0.3.11` → skipped (Python package release, not Bazel)
  - ❌ `0.3.11` → skipped (no prefix)

The workflow automatically strips the `bazel-v` prefix to determine the module version.

## BCR Templates

The BCR entry is generated from templates in the `.bcr` directory:

```
.bcr/
├── config.yml              # Configuration (moduleRoots)
└── bazel/                  # Templates for the envoy_toolshed module
    ├── metadata.template.json    # Module metadata (homepage, maintainers)
    ├── source.template.json      # Source archive URL and integrity
    └── presubmit.yml            # BCR CI tests
```

### Template Files

#### `.bcr/config.yml`

Specifies that the MODULE.bazel file is located in the `bazel/` subdirectory:

```yaml
moduleRoots:
- bazel
```

#### `.bcr/bazel/metadata.template.json`

Contains module metadata:

```json
{
    "homepage": "https://www.envoyproxy.io/",
    "maintainers": [
        {
            "github": "mmorel-35",
            "github_user_id": 6032561
        },
        {
            "github": "phlax",
            "github_user_id": 454682
        }
    ],
    "repository": [
        "github:envoyproxy/toolshed"
    ],
    "versions": [],
    "yanked_versions": {}
}
```

**To update maintainers**: Add your GitHub username and user ID to the `maintainers` array. Find your user ID with:
```bash
curl https://api.github.com/users/YOUR_USERNAME | jq .id
```

#### `.bcr/bazel/source.template.json`

Defines how to fetch the source archive:

```json
{
    "integrity": "",
    "strip_prefix": "{REPO}-{VERSION}/bazel",
    "url": "https://github.com/{OWNER}/{REPO}/archive/refs/tags/bazel-v{TAG}.tar.gz"
}
```

The workflow automatically:
- Substitutes `{OWNER}`, `{REPO}`, `{VERSION}`, `{TAG}` with actual values
- Calculates and fills in the `integrity` hash
- Extracts the `bazel/` subdirectory due to `strip_prefix`

#### `.bcr/bazel/presubmit.yml`

Defines the BCR CI tests that verify the module:

```yaml
matrix:
  unix_platform:
  - debian11
  - ubuntu2404
  - macos_arm64
  bazel:
  - 7.x
  - 8.x
  - 9.*
tasks:
  verify_targets:
    name: Verify build targets
    platform: ${{ unix_platform }}
    bazel: ${{ bazel }}
    build_targets:
    - "@envoy_toolshed//..."
```

This ensures the module builds successfully across multiple platforms and Bazel versions.

## Troubleshooting

### Workflow doesn't run

**Problem**: The publish workflow didn't trigger after creating a release.

**Solution**:
- Verify the tag matches the pattern `bazel-v*` (e.g., `bazel-v0.3.11`)
- Check the workflow runs at https://github.com/envoyproxy/toolshed/actions/workflows/publish-to-bcr.yml
- Tags like `v0.3.11` without the `bazel-` prefix are intentionally skipped

### Authentication failed when pushing to fork

**Problem**: The workflow fails with an authentication error.

**Solution**:
1. Verify the `BCR_PUBLISH_TOKEN` secret exists and is valid
2. Ensure the PAT has `repo` and `workflow` scopes
3. Check that the PAT hasn't expired
4. Confirm the fork exists at `envoyproxy/bazel-central-registry`

### Failed to open pull request

**Problem**: Entry was pushed to fork but PR creation failed.

**Solution**:
1. The PAT needs `workflow` scope to open PRs
2. Check if a PR already exists for this version
3. Manually create the PR:
   - Visit the fork: https://github.com/envoyproxy/bazel-central-registry
   - Find the pushed branch (named `envoy_toolshed-bazel-v{VERSION}`)
   - Click "Contribute" → "Open pull request"

### BCR CI tests fail

**Problem**: The PR is created but BCR's presubmit tests fail.

**Solution**:
1. Review the test failures in the BCR PR
2. Common issues:
   - Missing or incorrect dependencies in MODULE.bazel
   - Build targets don't exist or fail to build
   - Incompatible Bazel versions
3. Fix the issues and create a new release, or update `.bcr/bazel/presubmit.yml` if tests need adjustment

### Need to update templates after release

**Problem**: A release was created but the templates had errors.

**Solution**:
1. Fix the templates in the `.bcr` directory
2. Commit and push the fixes to `main`
3. Manually trigger the workflow:
   - Go to https://github.com/envoyproxy/toolshed/actions/workflows/publish-to-bcr.yml
   - Click "Run workflow"
   - Enter the same tag name
   - The workflow will use the updated templates from `main`

## Attestation Support

The workflow generates attestations for enhanced security and supply chain verification:

- **source.json**: Attests the generated source.json file
- **MODULE.bazel**: Attests the MODULE.bazel file
- **Release archive**: Attests the source archive

Attestations are uploaded to the GitHub Release and referenced in the BCR entry via `attestations.json`.

> [!NOTE]
> Attestations require that releases are published (not in draft state) and that the release tag exists in the repository. If you encounter attestation issues, verify that:
> - The release is marked as "Published" (not "Draft")
> - The tag exists in the repository (`git tag -l`)
> - The source archive is available at the expected URL

## References

- [publish-to-bcr Documentation](https://github.com/bazel-contrib/publish-to-bcr)
- [Bazel Central Registry](https://github.com/bazelbuild/bazel-central-registry)
- [Bzlmod User Guide](https://bazel.build/docs/bzlmod)
- [BCR Contribution Guidelines](https://github.com/bazelbuild/bazel-central-registry/blob/main/docs/README.md)

## Support

For issues related to:
- **BCR publishing workflow**: Open an issue in [bazel-contrib/publish-to-bcr](https://github.com/bazel-contrib/publish-to-bcr/issues)
- **BCR itself**: Open an issue in [bazelbuild/bazel-central-registry](https://github.com/bazelbuild/bazel-central-registry/issues)
- **toolshed module**: Open an issue in [envoyproxy/toolshed](https://github.com/envoyproxy/toolshed/issues)
