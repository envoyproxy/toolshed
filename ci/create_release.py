#!/usr/bin/env python3
"""Create GitHub releases and upload artifacts using envoy.github.release package."""

import argparse
import asyncio
import os
import pathlib
import sys
from typing import List

from envoy.github.release import GithubReleaseManager


async def create_release_with_artifacts(
    repository: str,
    version: str,
    artifacts_path: pathlib.Path,
    oauth_token: str,
    dry_run: bool = False,
) -> int:
    """Create a GitHub release and upload artifacts.

    Args:
        repository: GitHub repository in format owner/repo
        version: Version tag for the release (e.g., "0.1.28")
        artifacts_path: Path to directory containing artifacts to upload
        oauth_token: GitHub OAuth token for authentication
        dry_run: If True, don't actually create the release

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if dry_run:
        print(f"DRY RUN: Would create release for {version} in {repository}")
        print(f"DRY RUN: Would upload artifacts from {artifacts_path}")
        if artifacts_path.exists():
            artifacts = list(artifacts_path.rglob("*"))
            artifacts = [a for a in artifacts if a.is_file()]
            print(f"DRY RUN: Found {len(artifacts)} artifact(s) to upload:")
            for artifact in artifacts:
                print(f"DRY RUN:   - {artifact.name} ({artifact.stat().st_size} bytes)")
        return 0

    # Collect all artifacts from the artifacts directory
    artifacts: List[pathlib.Path] = []
    if artifacts_path.exists():
        artifacts = list(artifacts_path.rglob("*"))
        artifacts = [a for a in artifacts if a.is_file()]
        print(f"Found {len(artifacts)} artifact(s) to upload")
    else:
        print(f"Warning: Artifacts path {artifacts_path} does not exist")

    # Create the release
    try:
        async with GithubReleaseManager(
            path=str(artifacts_path),
            repository=repository,
            oauth_token=oauth_token,
            user="envoyproxy-bot",
            continues=False,  # Fail on errors
            create=True,  # Create if doesn't exist
        ) as manager:
            release = manager[version]
            
            # Check if release already exists
            if await release.exists:
                print(f"Release {version} already exists")
                # Still try to upload artifacts if provided
                if artifacts:
                    print(f"Uploading {len(artifacts)} artifact(s) to existing release")
                    result = await release.push(artifacts)
                    if result.get("errors"):
                        print(f"Errors uploading artifacts: {result['errors']}")
                        return 1
                    print(f"Successfully uploaded {len(result.get('assets', []))} artifacts")
                return 0
            
            # Create new release with artifacts
            print(f"Creating release {version} in {repository}")
            result = await release.create(assets=artifacts if artifacts else None)
            
            if result.get("errors"):
                print(f"Errors creating release: {result['errors']}")
                return 1
            
            print(f"Successfully created release {version}")
            if artifacts:
                print(f"Uploaded {len(result.get('assets', []))} artifact(s)")
            
            return 0
            
    except Exception as e:
        print(f"Error creating release: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create GitHub releases and upload artifacts"
    )
    parser.add_argument(
        "--repository",
        required=True,
        help="GitHub repository (owner/repo)",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Release version tag (e.g., 0.1.28)",
    )
    parser.add_argument(
        "--artifacts-path",
        type=pathlib.Path,
        default=pathlib.Path("./artifacts"),
        help="Path to artifacts directory (default: ./artifacts)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - don't actually create the release",
    )
    parser.add_argument(
        "--oauth-token",
        help="GitHub OAuth token (can also use GITHUB_TOKEN env var)",
    )
    
    args = parser.parse_args()
    
    # Get OAuth token from args or environment
    oauth_token = args.oauth_token or os.environ.get("GITHUB_TOKEN")
    if not oauth_token and not args.dry_run:
        print("Error: GitHub token required (use --oauth-token or GITHUB_TOKEN env var)", file=sys.stderr)
        return 1
    
    # Run the async function
    exit_code = asyncio.run(
        create_release_with_artifacts(
            repository=args.repository,
            version=args.version,
            artifacts_path=args.artifacts_path,
            oauth_token=oauth_token,
            dry_run=args.dry_run,
        )
    )
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
