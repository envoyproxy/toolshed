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
    "llvm-readelf",
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
    # Per-target-triple libc++ headers (e.g. include/x86_64-unknown-linux-gnu/c++/v1)
    "include/*/c++",
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
    # libclang C API shared library (referenced by envoy dynamic modules)
    "lib/libclang.so*",
    "lib/libclang*.dylib",
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
# Repository rule: extracted LLVM tree (for building minimal artifacts)
# =============================================================================

def _lib_glob_to_repo_globs(pattern):
    """Convert one allowlist entry to file-matching repo BUILD glob patterns."""
    final_segment = pattern.rsplit("/", 1)[-1]
    if "*" in final_segment and "." in final_segment:
        return [pattern]
    return [pattern + "/**/*"]

def _quoted_list(values):
    """Render a list literal safely for generated BUILD file content."""
    return repr(values)

def _llvm_version_major(version):
    return version.split(".")[0]

def render_llvm_repo_build(llvm_major):
    """Render BUILD.llvm_repo-shaped BUILD content for a minimal LLVM artifact."""
    return """package(default_visibility = ["//visibility:public"])

exports_files(glob(["bin/*", "lib/**", "include/**", "share/clang/*"], allow_empty = True))

filegroup(
    name = "clang",
    srcs = [
        "bin/clang",
        "bin/clang++",
        "bin/clang-cpp",
    ],
)

filegroup(
    name = "ld",
    srcs = [
        "bin/ld.lld",
        "bin/ld64.lld",
    ] + glob(["bin/wasm-ld"], allow_empty = True),
)

filegroup(
    name = "include",
    srcs = glob([
        "include/**",
        "lib/clang/{llvm_major}/include/**",
        "lib/clang/{llvm_major}/share/**",
        "lib/clang/{llvm_major}/libcxx-msan/include/**",
    ], allow_empty = True),
)

filegroup(
    name = "all_includes",
    srcs = [
        ":include",
        ":cxx_builtin_include",
        ":extra_config_site",
    ],
)

filegroup(
    name = "cxx_builtin_include",
    srcs = glob([
        "include/c++",
        "lib/clang/{llvm_major}/include",
        "lib/clang/{llvm_major}/share",
        "lib/clang/{llvm_major}/libcxx-msan/include",
        "lib/clang/{llvm_major}/libcxx-msan/source/include",
    ], allow_empty = True, exclude_directories = 0),
)

filegroup(
    name = "extra_config_site",
    srcs = glob(["include/*/c++/v1/__config_site"], allow_empty = True),
)

filegroup(
    name = "bin",
    srcs = glob(["bin/**"], allow_empty = True),
)

filegroup(
    name = "lib",
    srcs = glob([
        "lib/clang/{llvm_major}/lib",
        "lib/**/libc++*.a",
        "lib/**/libunwind.a",
        "lib/clang/{llvm_major}/libcxx-msan/lib",
    ], allow_empty = True, exclude_directories = 0),
)

filegroup(
    name = "lib_legacy",
    srcs = glob([
        "lib/clang/{llvm_major}/lib/**",
        "lib/**/libc++*.a",
        "lib/**/libunwind.a",
        "lib/clang/{llvm_major}/libcxx-msan/lib/**",
    ], allow_empty = True),
)

filegroup(
    name = "libclang_rt-asan-darwin",
    srcs = glob(["lib/clang/{llvm_major}/lib/darwin/libclang_rt.asan_osx_dynamic.dylib"], allow_empty = True),
)

filegroup(
    name = "libclang_rt-tsan-darwin",
    srcs = glob(["lib/clang/{llvm_major}/lib/darwin/libclang_rt.tsan_osx_dynamic.dylib"], allow_empty = True),
)

filegroup(
    name = "libclang_rt-ubsan-darwin",
    srcs = glob(["lib/clang/{llvm_major}/lib/darwin/libclang_rt.ubsan_osx_dynamic.dylib"], allow_empty = True),
)

filegroup(
    name = "ar",
    srcs = ["bin/llvm-ar"],
)

filegroup(
    name = "as",
    srcs = [
        "bin/clang",
        "bin/llvm-as",
    ],
)

filegroup(
    name = "nm",
    srcs = ["bin/llvm-nm"],
)

filegroup(
    name = "objcopy",
    srcs = ["bin/llvm-objcopy"],
)

filegroup(
    name = "objdump",
    srcs = ["bin/llvm-objdump"],
)

filegroup(
    name = "profdata",
    srcs = ["bin/llvm-profdata"],
)

filegroup(
    name = "dwp",
    srcs = ["bin/llvm-dwp"],
)

filegroup(
    name = "ranlib",
    srcs = ["bin/llvm-ranlib"],
)

filegroup(
    name = "readelf",
    srcs = ["bin/llvm-readelf"],
)

filegroup(
    name = "strip",
    srcs = ["bin/llvm-strip"],
)

filegroup(
    name = "symbolizer",
    srcs = ["bin/llvm-symbolizer"],
)

filegroup(
    name = "clang-tidy",
    srcs = ["bin/clang-tidy"],
)

filegroup(
    name = "clang-format",
    srcs = ["bin/clang-format"],
)

filegroup(
    name = "git-clang-format",
    srcs = ["bin/git-clang-format"],
)

filegroup(
    name = "libclang",
    srcs = glob(["lib/libclang.so*", "lib/libclang*.dylib"], allow_empty = True),
)
""".format(llvm_major = llvm_major)

LLVM_MINIMAL_LLVM_REPO_BUILD = render_llvm_repo_build(_llvm_version_major(LLVM_VERSION))

def _llvm_tarball_impl(ctx):
    """Downloads and extracts an LLVM upstream tarball hermetically.

    The extracted tree is exposed via filegroups so build rules can consume it
    directly without shelling out to tar/xz on the executor.
    """
    strip_prefix = "LLVM-{version}-{platform}".format(
        version = ctx.attr.version,
        platform = ctx.attr.platform,
    )
    ctx.download_and_extract(
        url = ctx.attr.url,
        sha256 = ctx.attr.sha256,
        stripPrefix = strip_prefix,
    )
    lib_globs = []
    for pattern in LLVM_MINIMAL_LIB_GLOBS:
        lib_globs.extend(_lib_glob_to_repo_globs(pattern))
    bin_globs = ["bin/{}".format(tool) for tool in LLVM_MINIMAL_BINS]
    ctx.file("BUILD.bazel", """
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "all",
    srcs = glob(["**/*"], allow_empty = True),
)

filegroup(
    name = "minimal_bins",
    srcs = glob({bin_globs}, allow_empty = True),
)

filegroup(
    name = "bin_all",
    srcs = glob(["bin/**"], allow_empty = True),
)

filegroup(
    name = "minimal_libs",
    srcs = glob({lib_globs}, allow_empty = True),
)
""".format(
        bin_globs = _quoted_list(bin_globs),
        lib_globs = _quoted_list(lib_globs),
    ))

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
        "version": attr.string(
            mandatory = True,
            doc = "LLVM version used in the upstream strip prefix",
        ),
        "platform": attr.string(
            mandatory = True,
            doc = "LLVM platform suffix used in the upstream strip prefix",
        ),
    },
    doc = "Downloads and extracts an upstream LLVM tarball for hermetic minimal LLVM artifact builds.",
)

# =============================================================================
# Build rule: assemble and strip the minimal bin/ tree
# =============================================================================

# Two-pass script:
#   Pass 1 — copy all allowlisted bins into DEST, preserving symlinks but also
#             copying each symlink's real target so no symlink is dangling.
#   Pass 2 — walk DEST, skip symlinks, probe each real file with llvm-readobj;
#             strip ELF/Mach-O objects (fatal on strip error) and skip scripts
#             like git-clang-format that are not valid object files.
#
# Portability note: readlink -f is GNU-only; use a portable loop to resolve
# the symlink chain without depending on GNU coreutils.
#
# Arguments: DEST STRIPPER READOBJ [name:src_path ...]
#   name     — output filename (e.g. "clang")
#   src_path — full path to the source file from bin_all inputs
#
# Symlink resolution is done entirely from $src (its dirname is the bin/
# directory, so the relative target resolves correctly inside the sandbox
# without requiring an explicit SRCDIR argument).
_LLVM_STRIP_BINS_SCRIPT = """
set -euo pipefail
DEST="$1"
STRIPPER="$2"
READOBJ="$3"
shift 3

# Pass 1: copy allowlisted bins; for symlinks also copy their real targets.
for spec in "$@"; do
    name="${spec%%:*}"
    src="${spec#*:}"
    if [ -L "$src" ]; then
        cp -P "$src" "$DEST/$name"
        # Portable readlink -f: walk the chain to the real file.
        # Cap at 40 iterations to catch circular symlinks (matches MAXSYMLINKS).
        real="$src"
        _depth=0
        while [ -L "$real" ]; do
            _depth=$((_depth + 1))
            if [ "$_depth" -gt 40 ]; then
                echo "symlink loop detected at $src" >&2
                exit 1
            fi
            target="$(readlink "$real")"
            case "$target" in
                /*) real="$target" ;;
                *)  real="$(dirname "$real")/$target" ;;
            esac
        done
        realbase="$(basename "$real")"
        if [ ! -f "$DEST/$realbase" ]; then
            cp "$real" "$DEST/$realbase"
        fi
    else
        cp "$src" "$DEST/$name"
    fi
done

# Pass 2: strip real (non-symlink) ELF/Mach-O files; skip non-objects.
# find -maxdepth 1 -type f naturally skips symlinks and handles an empty DEST.
# Piped while for portability; explicit || exit 1 ensures strip/mv failures
# propagate regardless of whether the subshell inherits set -e.
find "$DEST" -maxdepth 1 -type f | while IFS= read -r f; do
    if "$READOBJ" --file-headers "$f" > /dev/null 2>&1; then
        tmpf="${f}.strip-tmp"
        "$STRIPPER" -o "$tmpf" "$f" || exit 1
        mv "$tmpf" "$f" || exit 1
    fi
done
"""

def _llvm_minimal_strip_bins_impl(ctx):
    """Assembles and strips the minimal LLVM bin/ tree into a directory artifact.

    Uses declare_directory so that symlinks (e.g. clang → clang-22) AND their
    real targets (clang-22) are both preserved in the output tree; genrule outs
    cannot declare undeclared extra files, but a tree artifact contains all
    files created inside it.

    no-remote-exec keeps this action off RBE workers: the multi-GB LLVM tree
    is already present on the Bazel host and shipping it to remote workers
    would cause unnecessary large data transfers. The action remains
    remote-cacheable so the ~1 hr build result is reused across CI runs until
    the pinned LLVM version changes (roughly once a year).
    """
    out_dir = ctx.actions.declare_directory(
        "llvm_minimal_%s/bin" % ctx.attr.repo_suffix,
    )
    bin_files = ctx.files.bin_all
    stripper = ctx.file.stripper
    readobj = ctx.file.readobj

    if not bin_files:
        fail("bin_all has no files for repo_suffix=" + ctx.attr.repo_suffix)

    # Build a name → File map so we can pass explicit src_path per tool.
    # Tools absent from this tarball (e.g. macOS-only tools on a Linux tarball)
    # are simply not emitted in specs and are silently absent from the output.
    bin_by_name = {f.basename: f for f in bin_files}
    specs = [
        "%s:%s" % (name, bin_by_name[name].path)
        for name in ctx.attr.bins
        if name in bin_by_name
    ]

    ctx.actions.run_shell(
        # bin_files provide the source tree (allowlisted tools + symlink targets).
        inputs = bin_files,
        # stripper and readobj are declared as tools so Bazel tracks them in the
        # exec configuration and provides their runfiles automatically.
        tools = [stripper, readobj],
        outputs = [out_dir],
        command = _LLVM_STRIP_BINS_SCRIPT,
        arguments = [out_dir.path, stripper.path, readobj.path] + specs,
        mnemonic = "LlvmMinimalStripBins",
        progress_message = "Stripping LLVM minimal bins for " + ctx.attr.platform,
        execution_requirements = {"no-remote-exec": "1"},
    )

    return [DefaultInfo(files = depset([out_dir]))]

llvm_minimal_strip_bins = rule(
    implementation = _llvm_minimal_strip_bins_impl,
    attrs = {
        "bin_all": attr.label(
            mandatory = True,
            allow_files = True,
            doc = "Filegroup containing all files under bin/ of the LLVM tarball repo, " +
                  "including symlink targets (e.g. clang-22) not in the allowlist.",
        ),
        "bins": attr.string_list(
            mandatory = True,
            doc = "Allowlisted bin/ tool names to copy into the output tree.",
        ),
        "stripper": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "Host-executable llvm-strip binary.",
        ),
        "readobj": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "Host-executable llvm-readobj binary.",
        ),
        "repo_suffix": attr.string(
            mandatory = True,
            doc = "Suffix identifying the tarball repo (e.g. 'linux_x86_64').",
        ),
        "platform": attr.string(
            mandatory = True,
            doc = "Human-readable platform name used in progress messages.",
        ),
    },
    doc = "Assembles and strips the minimal LLVM bin/ tree for one platform.",
)

def setup_llvm_minimal_build():
    """Set up llvm_tarball_* repos needed to build the minimal LLVM artifacts.

    Creates three repositories:
      @llvm_tarball_linux_x86_64 — extracted Linux-X64 LLVM tree
      @llvm_tarball_linux_arm64  — extracted Linux-ARM64 LLVM tree
      @llvm_tarball_macos_arm64  — extracted macOS-ARM64 LLVM tree

    These are consumed by the //compile:llvm_minimal_* build targets.
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
            version = LLVM_VERSION,
            platform = platform,
        )

# =============================================================================
# Repository rule: consume pre-built minimal LLVM artifact from toolshed releases
# =============================================================================

_LLVM_MINIMAL_STUB_BUILD = """\
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
            url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/llvm-minimal-{llvm_version}-{platform}.tar.zst".format(
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
        ctx.file("BUILD.bazel", _LLVM_MINIMAL_STUB_BUILD)

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
