"""Minimal LLVM extraction: allowlist constants, repository rules, and setup functions.

This module defines:
  - LLVM_MINIMAL_BINS: explicit list of bin/ tool names to keep (single source of truth)
  - LLVM_MINIMAL_LIB_GLOBS: lib/include directory patterns to keep
  - llvm_tarball: repository rule that downloads a raw upstream LLVM tarball (used when
    building the minimal artifacts from source)
  - llvm_minimal: repository rule that downloads a pre-built minimal LLVM artifact from
    the toolshed bins release (used to consume the artifacts)
  - setup_llvm_minimal_build(): sets up llvm_tarball_* repos needed by genrule build targets
  - setup_llvm_minimal(): sets up llvm_minimal_* repos for consuming pre-built artifacts

To update the allowlist, edit LLVM_MINIMAL_BINS or LLVM_MINIMAL_LIB_GLOBS below and
rebuild/re-release.
"""

load("//:versions.bzl", "LLVM_DISTRIBUTIONS", "LLVM_VERSION", "VERSIONS")

# =============================================================================
# Allowlist: what to keep in the minimal LLVM extraction
# =============================================================================

# bin/ tools to keep.
# Sources: _toolchain_tools (toolchain/internal/common.bzl), tool_paths
# (toolchain/cc_toolchain_config.bzl), clang/ld/as filegroups
# (toolchain/BUILD.llvm_repo.tpl), aliased_tools (toolchain/aliases.bzl),
# and direct envoy/toolshed references.
LLVM_MINIMAL_BINS = [
    # Compiler driver + assembler
    "clang",
    "clang++",
    "clang-cpp",
    "llvm-as",
    # Linkers
    "lld",
    "ld.lld",
    "ld64.lld",
    "wasm-ld",
    # Binutils
    "llvm-ar",
    "llvm-ranlib",
    "llvm-nm",
    "llvm-objcopy",
    "llvm-objdump",
    "llvm-strip",
    "llvm-dwp",
    # Coverage / debug / profiling
    "llvm-cov",
    "llvm-profdata",
    "llvm-symbolizer",
    # macOS-only tools (harmless to include on Linux; only present on macOS tarballs)
    "llvm-libtool-darwin",
    "llvm-install-name-tool",
    # Formatting / analysis (toolshed clang_tidy integration + aliased_tools)
    "clang-tidy",
    "clang-format",
    "clang-apply-replacements",
    "clangd",
    "git-clang-format",
]

# lib/ and include/ patterns to keep.
# Entries that name a directory (no trailing glob) are copied recursively.
# Entries with shell-style globs are matched with find.
# Note: lib/clang/*/lib/** is kept in full (all compiler-rt / sanitizer runtimes
# including darwin dylibs, profile, xray, fuzzer — err on the side of inclusion).
LLVM_MINIMAL_LIB_GLOBS = [
    # Resource-dir builtin headers (includes fuzzer/FuzzedDataProvider.h)
    "lib/clang/*/include",
    # compiler-rt / sanitizer runtime archives + darwin dylibs (keep in full)
    "lib/clang/*/lib",
    # Sanitizer ignorelists that Clang auto-loads
    "lib/clang/*/share",
    # libc++ headers
    "include/c++",
    # Static libc++ and libc++abi for single-platform linking
    "lib/**/libc++*.a",
    "lib/**/libc++abi*.a",
    # Static libunwind + any shared libunwind
    "lib/**/libunwind*.a",
    "lib/**/libunwind*.so*",
    "lib/**/libunwind*.dylib",
    # libclang-cpp shared library (referenced by envoy on distro path)
    "lib/libclang-cpp.so*",
    "lib/libclang-cpp*.dylib",
]

# =============================================================================
# Platform metadata used by build targets and setup functions
# =============================================================================

# Map from the platform suffix used in artifact names to the upstream tarball filename.
# Keys match the platform component of the artifact name (e.g. "Linux-X64").
LLVM_MINIMAL_PLATFORMS = {
    "Linux-X64": "LLVM-%s-Linux-X64.tar.xz" % LLVM_VERSION,
    "Linux-ARM64": "LLVM-%s-Linux-ARM64.tar.xz" % LLVM_VERSION,
    "macOS-ARM64": "LLVM-%s-macOS-ARM64.tar.xz" % LLVM_VERSION,
}

# =============================================================================
# Repository rule: raw tarball download (for building minimal artifacts)
# =============================================================================

def _llvm_tarball_impl(ctx):
    """Downloads a raw LLVM upstream tarball without extracting it.

    The tarball is exposed as a file target so genrule build targets can take
    it as an input and process it (filter, strip, repack).
    """
    ctx.download(
        url = ctx.attr.url,
        output = ctx.attr.filename,
        sha256 = ctx.attr.sha256,
    )
    ctx.file("BUILD.bazel", """
package(default_visibility = ["//visibility:public"])
exports_files(["{filename}"])
""".format(filename = ctx.attr.filename))

llvm_tarball = repository_rule(
    implementation = _llvm_tarball_impl,
    attrs = {
        "url": attr.string(
            mandatory = True,
            doc = "URL of the LLVM tarball to download",
        ),
        "sha256": attr.string(
            mandatory = True,
            doc = "SHA256 hash of the LLVM tarball",
        ),
        "filename": attr.string(
            mandatory = True,
            doc = "Local filename to save the tarball as",
        ),
    },
    doc = "Downloads a raw upstream LLVM tarball for use as a genrule input when building minimal LLVM artifacts.",
)

def setup_llvm_minimal_build():
    """Set up llvm_tarball_* repos needed to build the minimal LLVM artifacts.

    Creates three repositories:
      @llvm_tarball_linux_x86_64 — raw Linux-X64 LLVM tarball
      @llvm_tarball_linux_arm64  — raw Linux-ARM64 LLVM tarball
      @llvm_tarball_macos_arm64  — raw macOS-ARM64 LLVM tarball

    These are consumed by the //compile:llvm_minimal_* genrule targets.
    """
    _platform_to_repo = {
        "Linux-X64": "llvm_tarball_linux_x86_64",
        "Linux-ARM64": "llvm_tarball_linux_arm64",
        "macOS-ARM64": "llvm_tarball_macos_arm64",
    }
    for platform, repo_name in _platform_to_repo.items():
        filename = LLVM_MINIMAL_PLATFORMS[platform]
        sha256 = LLVM_DISTRIBUTIONS[filename]
        url = "https://github.com/llvm/llvm-project/releases/download/llvmorg-{version}/{filename}".format(
            version = LLVM_VERSION,
            filename = filename,
        )
        llvm_tarball(
            name = repo_name,
            url = url,
            sha256 = sha256,
            filename = filename,
        )

# =============================================================================
# Repository rule: consume pre-built minimal LLVM artifact from toolshed releases
# =============================================================================

_LLVM_MINIMAL_BUILD = """\
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "all",
    srcs = glob(["**"]),
)

filegroup(
    name = "bin",
    srcs = glob(["bin/**"]),
)

filegroup(
    name = "lib",
    srcs = glob(["lib/**"]),
)

filegroup(
    name = "include",
    srcs = glob(["include/**"]),
)
"""

def _llvm_minimal_impl(ctx):
    """Downloads a pre-built minimal LLVM artifact from toolshed bins releases."""
    platform = ctx.attr.platform
    version = ctx.attr.version
    llvm_version = ctx.attr.llvm_version
    sha256 = ctx.attr.sha256

    if sha256:
        strip_prefix = "llvm-minimal-{llvm_version}-{platform}".format(
            llvm_version = llvm_version,
            platform = platform,
        )
        ctx.download_and_extract(
            url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/llvm-minimal-{llvm_version}-{platform}.tar.xz".format(
                version = version,
                llvm_version = llvm_version,
                platform = platform,
            ),
            sha256 = sha256,
            stripPrefix = strip_prefix,
        )
    else:
        # No hash available yet — create a stub empty repository so Bazel can
        # still load the repo without a network hit.  ctx.file() is idiomatic
        # and works portably without relying on external commands.
        ctx.file("bin/.gitkeep", "")
        ctx.file("lib/.gitkeep", "")
        ctx.file("include/.gitkeep", "")

    ctx.file("BUILD.bazel", _LLVM_MINIMAL_BUILD)

llvm_minimal = repository_rule(
    implementation = _llvm_minimal_impl,
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "Toolshed bins release version (e.g., '0.2.0')",
        ),
        "llvm_version": attr.string(
            mandatory = True,
            doc = "LLVM version string (e.g., '22.1.8')",
        ),
        "platform": attr.string(
            mandatory = True,
            doc = "Platform suffix matching the artifact name: 'Linux-X64', 'Linux-ARM64', or 'macOS-ARM64'",
            values = ["Linux-X64", "Linux-ARM64", "macOS-ARM64"],
        ),
        "sha256": attr.string(
            default = "",
            doc = "SHA256 hash of the artifact. Empty string skips download and creates a stub.",
        ),
    },
    doc = "Downloads a pre-built minimal LLVM artifact from the toolshed bins release.",
)

def setup_llvm_minimal(
        linux_x64_version = None,
        linux_x64_sha256 = None,
        linux_arm64_version = None,
        linux_arm64_sha256 = None,
        macos_arm64_version = None,
        macos_arm64_sha256 = None):
    """Set up minimal LLVM repositories for the three supported platforms.

    Creates:
      @llvm_minimal_linux_x64   — minimal LLVM for Linux x86_64
      @llvm_minimal_linux_arm64 — minimal LLVM for Linux aarch64
      @llvm_minimal_macos_arm64 — minimal LLVM for macOS arm64

    SHA256 values default to VERSIONS['llvm_minimal_sha256'][platform] from
    versions.bzl (empty string => stub repository until first release).
    """
    llvm_version = VERSIONS["llvm"]
    sha256_map = VERSIONS.get("llvm_minimal_sha256", {})
    bins_release = VERSIONS["bins_release"]

    _configs = [
        ("Linux-X64", "llvm_minimal_linux_x64", linux_x64_version, linux_x64_sha256),
        ("Linux-ARM64", "llvm_minimal_linux_arm64", linux_arm64_version, linux_arm64_sha256),
        ("macOS-ARM64", "llvm_minimal_macos_arm64", macos_arm64_version, macos_arm64_sha256),
    ]

    for platform, repo_name, ver, sha in _configs:
        # Use sha256_map fallback when sha is None (direct call with no argument) OR
        # when sha is "" (via the extension with no sha256 attr set — attr.string never
        # returns None, so we must treat empty string as "use the default" too).
        sha256 = sha if (sha != None and sha != "") else sha256_map.get(platform, "")
        llvm_minimal(
            name = repo_name,
            version = ver if ver != None else bins_release,
            llvm_version = llvm_version,
            platform = platform,
            sha256 = sha256,
        )
