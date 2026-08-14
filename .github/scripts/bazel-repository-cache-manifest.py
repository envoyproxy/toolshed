#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any


LLVM_BUCKETS = {
    "llvm-x86": (
        "//compile:extensions.bzl%llvm_minimal_build_extension",
        "llvm_tarball_linux_x86_64",
    ),
    "llvm-aarch": (
        "//compile:extensions.bzl%llvm_minimal_build_extension",
        "llvm_tarball_linux_arm64",
    ),
    "llvm-macos": (
        "//compile:extensions.bzl%llvm_minimal_build_extension",
        "llvm_tarball_macos_arm64",
    ),
}

LIBCXX_BUCKETS = {
    "llvm-x86": (
        "//compile:extensions.bzl%libcxx_extension",
        "llvm_libcxx_x86_64",
    ),
    "llvm-aarch": (
        "//compile:extensions.bzl%libcxx_extension",
        "llvm_libcxx_aarch64",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("check", "write"):
        subparser = subparsers.add_parser(command)
        add_manifest_source_args(subparser)

    outputs = subparsers.add_parser("github-outputs")
    outputs.add_argument("--manifest-path", type=Path, required=True)
    outputs.add_argument("--repo-cache-path", type=Path, required=True)
    outputs.add_argument("--output", type=Path, default=None)

    presence = subparsers.add_parser("presence")
    presence.add_argument("--manifest-path", type=Path, required=True)
    presence.add_argument("--repo-cache-path", type=Path, required=True)
    presence.add_argument("--output", type=Path, default=None)

    return parser.parse_args()


def add_manifest_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--module-path", type=Path, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def read_v8_version(module_path: Path) -> str:
    match = re.search(
        r'bazel_dep\s*\(\s*name\s*=\s*"v8"\s*,\s*version\s*=\s*"([^"]+)"',
        module_path.read_text(),
    )
    if not match:
        raise ValueError(f"Unable to find v8 bazel_dep in {module_path}")
    return match.group(1)


def lock_sha256(lock_data: dict[str, Any], extension: str, repo: str) -> str:
    return lock_data["moduleExtensions"][extension]["general"]["generatedRepoSpecs"][repo][
        "attributes"
    ]["sha256"]


def read_llvm_hashes(lock_data: dict[str, Any]) -> dict[str, str]:
    hashes = {
        bucket: lock_sha256(lock_data, extension, repo)
        for bucket, (extension, repo) in LLVM_BUCKETS.items()
    }
    for bucket, (extension, repo) in LIBCXX_BUCKETS.items():
        libcxx_hash = lock_sha256(lock_data, extension, repo)
        if libcxx_hash != hashes[bucket]:
            raise ValueError(
                f"{bucket} mismatch between {extension}/{repo} ({libcxx_hash}) "
                f"and llvm_minimal_build_extension ({hashes[bucket]})"
            )
    return hashes


def v8_source_json_url(lock_data: dict[str, Any], version: str) -> str:
    suffix = f"/modules/v8/{version}/source.json"
    matches = [
        url
        for url in lock_data["registryFileHashes"]
        if url.endswith(suffix)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one v8 source.json URL for version {version}, found {matches}"
        )
    return matches[0]


def fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def integrity_to_sha256(integrity: str) -> str:
    try:
        algorithm, value = integrity.split("-", 1)
    except ValueError as exc:
        raise ValueError(f"Unsupported integrity value: {integrity}") from exc
    if algorithm != "sha256":
        raise ValueError(f"Unsupported integrity algorithm: {algorithm}")
    return base64.b64decode(value).hex()


def expected_manifest(module_path: Path, lock_path: Path) -> dict[str, str]:
    lock_data = load_json(lock_path)
    hashes = read_llvm_hashes(lock_data)
    version = read_v8_version(module_path)
    source = fetch_json(v8_source_json_url(lock_data, version))
    hashes["v8-source"] = integrity_to_sha256(source["integrity"])
    return hashes


def load_manifest(manifest_path: Path) -> dict[str, str]:
    manifest = load_json(manifest_path)
    return {str(key): str(value) for key, value in manifest.items()}


def write_manifest(manifest_path: Path, manifest: dict[str, str]) -> None:
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def github_output_path(path: Path | None) -> Path:
    if path is not None:
        return path
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        raise ValueError("Missing --output and GITHUB_OUTPUT is not set")
    return Path(output)


def append_output(path: Path, name: str, value: str) -> None:
    with path.open("a") as f:
        if "\n" in value:
            print(f"{name}<<EOF", file=f)
            print(value, file=f)
            print("EOF", file=f)
        else:
            print(f"{name}={value}", file=f)


def emit_github_outputs(manifest_path: Path, repo_cache_path: Path, output_path: Path) -> None:
    manifest = load_manifest(manifest_path)
    hash_root = repo_cache_path / "content_addressable" / "sha256"
    append_output(output_path, "llvm_x86_sha256", manifest["llvm-x86"])
    append_output(output_path, "llvm_aarch_sha256", manifest["llvm-aarch"])
    append_output(output_path, "llvm_macos_sha256", manifest["llvm-macos"])
    append_output(output_path, "v8_source_sha256", manifest["v8-source"])
    append_output(output_path, "llvm_x86_path", str(hash_root / manifest["llvm-x86"]))
    append_output(output_path, "llvm_aarch_path", str(hash_root / manifest["llvm-aarch"]))
    append_output(output_path, "llvm_macos_path", str(hash_root / manifest["llvm-macos"]))
    append_output(output_path, "v8_source_path", str(hash_root / manifest["v8-source"]))
    rest_lines = [str(repo_cache_path)]
    for bucket in ("llvm-x86", "llvm-aarch", "llvm-macos", "v8-source"):
        rest_lines.append(f"!{hash_root / manifest[bucket]}")
    append_output(output_path, "rest_path", "\n".join(rest_lines))


def bucket_present(repo_cache_path: Path, sha256: str) -> bool:
    bucket = repo_cache_path / "content_addressable" / "sha256" / sha256
    return bucket.exists() and any(path.is_file() for path in bucket.rglob("*"))


def rest_present(repo_cache_path: Path, manifest: dict[str, str]) -> bool:
    if not repo_cache_path.exists():
        return False
    excluded = {
        (repo_cache_path / "content_addressable" / "sha256" / sha256).resolve()
        for sha256 in manifest.values()
    }
    for path in repo_cache_path.rglob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if any(excluded_path == resolved or excluded_path in resolved.parents for excluded_path in excluded):
            continue
        return True
    return False


def emit_presence(manifest_path: Path, repo_cache_path: Path, output_path: Path) -> None:
    manifest = load_manifest(manifest_path)
    append_output(
        output_path,
        "llvm_x86_present",
        str(bucket_present(repo_cache_path, manifest["llvm-x86"])).lower(),
    )
    append_output(
        output_path,
        "llvm_aarch_present",
        str(bucket_present(repo_cache_path, manifest["llvm-aarch"])).lower(),
    )
    append_output(
        output_path,
        "llvm_macos_present",
        str(bucket_present(repo_cache_path, manifest["llvm-macos"])).lower(),
    )
    append_output(
        output_path,
        "v8_source_present",
        str(bucket_present(repo_cache_path, manifest["v8-source"])).lower(),
    )
    append_output(output_path, "rest_present", str(rest_present(repo_cache_path, manifest)).lower())


def main() -> int:
    args = parse_args()
    if args.command in {"check", "write"}:
        manifest = expected_manifest(args.module_path, args.lock_path)
        if args.command == "write":
            write_manifest(args.manifest_path, manifest)
            return 0
        current = load_manifest(args.manifest_path)
        if current != manifest:
            print("Repository cache manifest is out of date.", file=sys.stderr)
            print("Expected:", file=sys.stderr)
            print(json.dumps(manifest, indent=2, sort_keys=True), file=sys.stderr)
            print("Found:", file=sys.stderr)
            print(json.dumps(current, indent=2, sort_keys=True), file=sys.stderr)
            return 1
        return 0

    output_path = github_output_path(args.output)
    output_path.write_text("")
    if args.command == "github-outputs":
        emit_github_outputs(args.manifest_path, args.repo_cache_path, output_path)
        return 0
    if args.command == "presence":
        emit_presence(args.manifest_path, args.repo_cache_path, output_path)
        return 0
    raise ValueError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
