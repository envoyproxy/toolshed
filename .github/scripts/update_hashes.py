#!/usr/bin/env python3
"""Update SHA256 hashes in bazel/versions.bzl from GitHub Actions outputs."""

import os
import re
import sys


def update_versions_file(file_path: str, version: str, hashes: dict) -> bool:
    """Update the versions.bzl file with new version and hashes.
    
    Args:
        file_path: Path to versions.bzl file
        version: New bins_release version
        hashes: Dictionary of hash values from GitHub Actions
        
    Returns:
        True if any changes were made, False otherwise
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Update bins_release version
    content = re.sub(
        r'"bins_release": "[^"]*"',
        f'"bins_release": "{version}"',
        content
    )
    
    # Update sanitizer library hashes
    for lib in ['msan', 'tsan']:
        key = f'{lib}_libs_sha256'
        if key in hashes:
            content = re.sub(
                rf'"{key}": "[a-f0-9]*"',
                f'"{key}": "{hashes[key]}"',
                content
            )
    
    # Update glint hashes
    for arch in ['amd64', 'arm64']:
        key = f'glint_{arch}_sha256'
        if key in hashes:
            # Match within glint_sha256 dictionary
            pattern = rf'("glint_sha256":\s*\{{[^}}]*"{arch}":\s*")([a-f0-9]+)(")'
            content = re.sub(pattern, rf'\g<1>{hashes[key]}\g<3>', content)
    
    # Update sysroot hashes in nested structure
    for glibc in ['2.31', '2.28']:
        for variant in ['base', '13']:
            for arch in ['amd64', 'arm64']:
                key = f'sysroot_{glibc}_{variant}_{arch}'
                if key in hashes:
                    # Pattern to match the hash within the nested structure
                    # "2.31": { ... "base": { ... "amd64": "hash", ...
                    glibc_escaped = re.escape(glibc)
                    # Use DOTALL flag to match across newlines
                    pattern = (
                        rf'("{glibc_escaped}":\s*\{{.*?'
                        rf'"{variant}":\s*\{{.*?'
                        rf'"{arch}":\s*")([a-f0-9]+)(")'
                    )
                    content = re.sub(pattern, rf'\g<1>{hashes[key]}\g<3>', content, flags=re.DOTALL)
    
    # Update legacy sysroot hashes
    for arch in ['amd64', 'arm64']:
        key = f'sysroot_{arch}_sha256'
        if key in hashes:
            content = re.sub(
                rf'"{key}": "[a-f0-9]*"',
                f'"{key}": "{hashes[key]}"',
                content
            )
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False


def main():
    """Main entry point."""
    # Get inputs from environment (GitHub Actions outputs)
    version = os.environ.get('VERSION', '')
    if not version:
        print("Error: VERSION environment variable not set")
        sys.exit(1)
    
    # Collect all hash outputs from GitHub Actions
    hashes = {}
    
    # Sanitizer libs
    for lib in ['msan', 'tsan']:
        key = f'{lib}_libs_sha256'
        value = os.environ.get(key.upper(), '')
        if value:
            hashes[key] = value
    
    # Glint binaries
    for arch in ['amd64', 'arm64']:
        key = f'glint_{arch}_sha256'
        value = os.environ.get(key.upper(), '')
        if value:
            hashes[key] = value
    
    # Sysroot archives
    for glibc in ['2.31', '2.28']:
        for variant in ['base', '13']:
            for arch in ['amd64', 'arm64']:
                # Environment variable names can't have dots, so they're replaced with underscores
                key = f'sysroot_{glibc}_{variant}_{arch}'
                env_key = key.replace('.', '_').upper()
                value = os.environ.get(env_key, '')
                if value:
                    hashes[key] = value
    
    # Legacy sysroot hashes
    for arch in ['amd64', 'arm64']:
        key = f'sysroot_{arch}_sha256'
        value = os.environ.get(key.upper(), '')
        if value:
            hashes[key] = value
    
    file_path = 'bazel/versions.bzl'
    
    print(f"Updating {file_path} with version {version}")
    print(f"Found {len(hashes)} hash values to update")
    
    changed = update_versions_file(file_path, version, hashes)
    
    if changed:
        print("✓ File updated successfully")
        sys.exit(0)
    else:
        print("ℹ No changes made to file")
        sys.exit(0)


if __name__ == '__main__':
    main()
