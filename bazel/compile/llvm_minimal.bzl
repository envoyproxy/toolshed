"""Minimal LLVM extraction: allowlist constants, repository rules, and setup functions.

This module defines:
  - LLVM_MINIMAL_BINS: explicit list of bin/ tool names to keep (single source of truth)
  - LLVM_MINIMAL_LIB_GLOBS: lib/include directory patterns to keep
  - llvm_tarball: repository rule that downloads a raw upstream LLVM tarball (used when
    building the minimal artifacts from source)
  - setup_llvm_minimal(): sets up llvm_minimal_* repos used by consumers
  - setup_llvm_minimal_build(): sets up llvm_tarball_* repos needed by genrule build targets
  - llvm_toolchain_alias: repository rule that resolves llvm_toolchain_llvm to the
    matching host-arch llvm_minimal_* repo

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
#
# Symlink aliases and their real targets are BOTH listed explicitly so that
# each allowlisted entry can be copied verbatim (preserving linkiness) without
# any symlink-chain resolution:
#   clang, clang++, clang-cpp        -> clang-22 (the real clang binary)
#   ld.lld, ld64.lld, wasm-ld        -> lld      (the real linker binary)
LLVM_MINIMAL_BINS = [
    # Compiler driver + assembler
    "clang",
    "clang++",
    "clang-cpp",
    # Real clang binary that clang/clang++/clang-cpp symlink to.
    "clang-22",
    "llvm-as",
    # Linkers (ld.lld/ld64.lld/wasm-ld symlink to the real `lld`).
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
    "llvm-readobj",
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
    # libclang / libTooling C++ API headers (referenced by the Envoy openssl
    # prefixer, which #includes "clang/AST/...", "clang-c/...", and transitively
    # "llvm/...").
    "include/clang",
    "include/clang-c",
    "include/llvm",
    "include/llvm-c",
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
    # libLLVM shared library (referenced by envoy openssl/prefixer on LLVM_PATH build)
    "lib/libLLVM.so*",
    "lib/libLLVM*.dylib",
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

def _llvm_minimal_repo_impl(ctx):
    """Downloads and extracts a released minimal LLVM artifact."""
    if ctx.attr.sha256:
        ctx.download_and_extract(
            url = ctx.attr.url,
            sha256 = ctx.attr.sha256,
            stripPrefix = ctx.attr.strip_prefix,
        )
    else:
        # Placeholder state before first release: create an empty repo so callers
        # that do not reference it are not broken.
        result = ctx.execute(["mkdir", "-p", "bin", "include", "lib", "share/clang"])
        if result.return_code:
            fail("Failed to create placeholder llvm_minimal repo directories: " + result.stderr)
    ctx.file("BUILD.bazel", LLVM_MINIMAL_LLVM_REPO_BUILD)

llvm_minimal_repo = repository_rule(
    implementation = _llvm_minimal_repo_impl,
    attrs = {
        "url": attr.string(
            mandatory = True,
            doc = "URL of the released minimal LLVM artifact",
        ),
        "sha256": attr.string(
            default = "",
            doc = "SHA256 hash of the released minimal LLVM artifact. Empty string skips download.",
        ),
        "strip_prefix": attr.string(
            mandatory = True,
            doc = "Archive strip prefix for the released minimal LLVM artifact",
        ),
    },
    doc = "Downloads and extracts a released minimal LLVM artifact.",
)

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

exports_files(glob(["bin/**"], allow_empty = True))

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

def _normalize_llvm_toolchain_alias_os(os_name):
    """Normalize repository_ctx.os.name for llvm_toolchain_llvm alias selection."""
    os_name = os_name.lower()
    if os_name == "linux":
        return "linux"
    if os_name == "mac os x" or os_name == "darwin":
        return "macos"
    return None

def _normalize_llvm_toolchain_alias_arch(arch):
    """Normalize repository_ctx.os.arch for llvm_toolchain_llvm alias selection."""
    arch = arch.lower()
    if arch == "x86_64" or arch == "amd64":
        return "x86_64"
    if arch == "aarch64" or arch == "arm64":
        return "aarch64"
    return None

def _get_llvm_toolchain_alias_platform_info(ctx):
    """Resolve the host platform to the matching llvm_minimal_* repo."""
    os_name = _normalize_llvm_toolchain_alias_os(ctx.os.name)
    arch = _normalize_llvm_toolchain_alias_arch(ctx.os.arch)

    if os_name == "linux":
        if arch == "x86_64":
            return {
                "minimal_repo": "llvm_minimal_linux_x64",
            }
        elif arch == "aarch64":
            return {
                "minimal_repo": "llvm_minimal_linux_arm64",
            }
    # Only macOS ARM64 minimal artifacts are currently published.
    elif os_name == "macos" and arch == "aarch64":
        return {
            "minimal_repo": "llvm_minimal_macos_arm64",
        }

    fail("Unsupported host platform for llvm_toolchain_llvm alias: {} {}. Supported combinations are linux/x86_64, linux/aarch64, and macos/arm64.".format(ctx.os.name, ctx.os.arch))

def _symlink_dir_children(ctx, source_dir, relpath):
    """Symlink each child of source_dir individually into relpath in this repo.

    A directory symlink (ctx.symlink on the dir itself) is NOT followed by
    Bazel when sourcing individual files for a filegroup src, so bzlmod
    reports "missing input file '...//:bin/llvm-nm'". Symlinking each child as
    its own file/dir symlink makes every entry a real, stageable input under
    both bzlmod and WORKSPACE.
    """
    for child in source_dir.readdir():
        ctx.symlink(child, "{}/{}".format(relpath, child.basename))

def _ensure_repo_dir(ctx, source_root, relpath):
    """Populate relpath by per-child symlinks from the source dir, or create it."""
    source_dir = source_root.get_child(relpath)
    if source_dir.exists:
        _symlink_dir_children(ctx, source_dir, relpath)
    else:
        result = ctx.execute(["mkdir", "-p", relpath])
        if result.return_code:
            fail("Failed to create llvm_toolchain_llvm alias directory '{}': {}".format(relpath, result.stderr))

def _llvm_toolchain_alias_impl(ctx):
    """Create a host-arch alias repo backed by the matching minimal LLVM artifact.

    bin/, include/ and lib/ contents are symlinked in per-child from the
    host-arch minimal repo, so every tool/header lives in this repo's own
    package as a real (file or dir) symlink. Targets are therefore real
    filegroups over those local files (NOT alias() into the minimal repo):
    aliasing would leave the filegroup's source file (e.g. bin/llvm-nm) owned
    by the minimal repo, which fails runfiles staging with
    "missing input file '...//:bin/llvm-nm'". Per-child (not whole-directory)
    symlinks are required because Bazel does not follow a symlinked package
    directory when sourcing individual filegroup inputs.
    """
    platform_info = _get_llvm_toolchain_alias_platform_info(ctx)
    minimal_repo = platform_info["minimal_repo"]
    minimal_root = ctx.path(Label("@{}//:BUILD.bazel".format(minimal_repo))).dirname

    _ensure_repo_dir(ctx, minimal_root, "bin")
    _ensure_repo_dir(ctx, minimal_root, "include")
    _ensure_repo_dir(ctx, minimal_root, "lib")

    ctx.file("BUILD.bazel", LLVM_MINIMAL_LLVM_REPO_BUILD)

llvm_toolchain_alias = repository_rule(
    implementation = _llvm_toolchain_alias_impl,
    attrs = {},
    doc = "Creates the host-arch llvm_toolchain_llvm alias backed by llvm_minimal_* repos.",
)

# =============================================================================
# Build rule: assemble and strip the minimal bin/ tree
# =============================================================================

# Three-pass script implementing the intended algorithm:
#   Pass 1 — copy EXACTLY the allowlisted files with `cp -P` and no symlink
#            unwrapping or reconstruction. A symlink stays a symlink and a real
#            file stays a real file.
#   Pass 2 — fail loudly on dangling symlinks in DEST before stripping.
#   Pass 3 — walk DEST, skip symlinks and anything that cannot be stripped
#            (probed via llvm-readobj --file-headers), and strip the rest.
#            `find -maxdepth 1 -type f` skips symlinks; the readobj probe skips
#            scripts like git-clang-format that are not valid object files.
#
# Arguments: DEST STRIPPER READOBJ [name:src_path ...]
#   name     — output filename (e.g. "clang" or "clang-22")
#   src_path — full path to the source file from bin_all inputs
_LLVM_STRIP_BINS_SCRIPT = """
set -euo pipefail
DEST="$1"
STRIPPER="$2"
READOBJ="$3"
shift 3
mkdir -p "$DEST"

# Pass 1: exact copy; cp -P never dereferences.
for spec in "$@"; do
    name="${spec%%:*}"
    src="${spec#*:}"
    cp -P "$src" "$DEST/$name"
done

# Pass 2: fail loudly on dangling symlinks before stripping.
dangling=0
for l in "$DEST"/*; do
    if [ -L "$l" ] && [ ! -e "$l" ]; then
        echo "DANGLING SYMLINK: $l -> $(readlink "$l")" >&2
        dangling=1
    fi
done
[ "$dangling" -eq 0 ] || { echo "ERROR: dangling symlinks in $DEST" >&2; exit 1; }

# Pass 3: strip real (non-symlink) ELF/Mach-O files; skip symlinks and
# non-objects.  find -maxdepth 1 -type f skips symlinks and handles an empty
# DEST.  Piped while for portability; explicit || exit 1 ensures strip/mv
# failures propagate regardless of whether the subshell inherits set -e.
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
        "llvm_minimal_%s_bins_src" % ctx.attr.repo_suffix,
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
        arguments = [out_dir.path + "/bin", stripper.path, readobj.path] + specs,
        mnemonic = "LlvmMinimalStripBins",
        progress_message = "Stripping LLVM minimal bins for " + ctx.attr.platform,
        execution_requirements = {
            "no-remote-exec": "1",
            "no-sandbox": "1",
        },
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

def setup_llvm_minimal(
        linux_x64_sha256 = None,
        linux_arm64_sha256 = None,
        macos_arm64_sha256 = None):
    """Set up llvm_minimal_* repos used by consumers."""
    platform_to_repo = {
        "Linux-X64": ("llvm_minimal_linux_x64", linux_x64_sha256),
        "Linux-ARM64": ("llvm_minimal_linux_arm64", linux_arm64_sha256),
        "macOS-ARM64": ("llvm_minimal_macos_arm64", macos_arm64_sha256),
    }
    for platform, (repo_name, override_sha256) in platform_to_repo.items():
        config = VERSIONS[repo_name]
        llvm_minimal_repo(
            name = repo_name,
            url = config["url"].format(**config),
            sha256 = override_sha256 if override_sha256 != None else config["sha256"],
            strip_prefix = config["strip_prefix"].format(**config),
        )
