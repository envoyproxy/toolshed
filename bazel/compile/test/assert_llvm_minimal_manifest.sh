#!/bin/bash
set -euo pipefail

: "${MTREE:?MTREE must be set}"
: "${PLATFORM:?PLATFORM must be set}"
: "${LLVM_MAJOR:?LLVM_MAJOR must be set}"
: "${BINS:?BINS must be set}"
: "${LIB_GLOBS:?LIB_GLOBS must be set}"

python3 - "$MTREE" "$PLATFORM" "$LLVM_MAJOR" "$BINS" "$LIB_GLOBS" <<'PY'
import fnmatch
import re
import sys

mtree_path, platform, llvm_major, bins_csv, lib_globs_csv = sys.argv[1:6]

with open(mtree_path, encoding="utf-8") as fh:
    paths = []
    for raw in fh:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        first = line.split(maxsplit=1)[0]
        if first in (".", ".."):
            continue
        p = first.lstrip("./")
        if p:
            paths.append(p)

if not paths:
    raise SystemExit(f"FAIL: mtree manifest has no paths: {mtree_path}")

def has_glob(glob_pat: str) -> bool:
    return any(fnmatch.fnmatch(p, glob_pat) for p in paths)

def require_glob(glob_pat: str, message: str) -> None:
    if not has_glob(glob_pat):
        raise SystemExit(f"FAIL: {message} (missing glob: {glob_pat})")

# Every expected bin from LLVM_MINIMAL_BINS (platform-filtered in BUILD) must exist.
for tool in [b for b in bins_csv.split(",") if b]:
    require_glob(f"*/bin/{tool}", f"missing required tool bin/{tool}")

# Assert allowlist materialization for platform-relevant globs.
for glob_pat in [g for g in lib_globs_csv.split(",") if g]:
    final_segment = glob_pat.rsplit("/", 1)[-1]
    if "*" in final_segment and "." in final_segment:
        continue
    if platform.startswith("macOS") and glob_pat == "include/*/c++":
        continue
    if glob_pat == "lib/clang/*/share":
        continue
    require_glob(f"*/{glob_pat}/**", f"allowlist glob produced no files: {glob_pat}")

# Envoy/toolshed superset assertions.
require_glob("*/BUILD.bazel", "missing root BUILD.bazel in artifact")
require_glob(f"*/lib/clang/{llvm_major}/include/**", "missing lib/clang/<major>/include contents")
require_glob(f"*/lib/clang/{llvm_major}/lib/**", "missing lib/clang/<major>/lib contents")
require_glob("*/include/c++/**", "missing include/c++ headers")

if platform == "Linux-X64":
    require_glob("*/include/x86_64-unknown-linux-gnu/c++/v1/**", "missing x86_64 triple libc++ include tree")
if platform == "Linux-ARM64":
    require_glob("*/include/aarch64-unknown-linux-gnu/c++/v1/**", "missing aarch64 triple libc++ include tree")

if platform.startswith("Linux"):
    require_glob("*/lib/**/libc++.a", "missing libc++.a")
    require_glob("*/lib/**/libc++abi.a", "missing libc++abi.a")
    require_glob("*/lib/**/libunwind.a", "missing libunwind.a")
    require_glob("*/lib/libclang.so*", "missing libclang.so* (Envoy dynamic modules)")
    require_glob("*/lib/libclang-cpp.so*", "missing libclang-cpp.so*")
    require_glob("*/lib/libLLVM.so*", "missing libLLVM.so* (envoy openssl/prefixer LLVM_PATH build)")
    if not any(re.search(r"/lib/libclang-cpp\.so\.\d+\.\d+$", p) for p in paths):
        raise SystemExit("FAIL: missing versioned libclang-cpp.so.<major.minor>")
else:
    require_glob("*/lib/libunwind*.dylib", "missing libunwind dylib")
    require_glob("*/lib/libclang*.dylib", "missing libclang*.dylib")

# share dir is optional upstream; if present, ensure it is non-empty.
if has_glob(f"*/lib/clang/{llvm_major}/share") or has_glob(f"*/lib/clang/{llvm_major}/share/**"):
    require_glob(f"*/lib/clang/{llvm_major}/share/**", "lib/clang/<major>/share exists but has no files")

print(f"PASS: llvm minimal manifest checks passed for {platform}")
PY
