"""Minimal LLVM extraction: allowlist constants, repository rules, and setup functions.

This module defines:
  - LLVM_MINIMAL_BINS: explicit list of bin/ tool names to keep (single source of truth)
  - LLVM_MINIMAL_LIB_GLOBS: lib/include directory patterns to keep
  - llvm_tarball: repository rule that downloads a raw upstream LLVM tarball (used when
    building the minimal artifacts from source)
  - setup_llvm_minimal(): sets up llvm_minimal_* repos used by consumers
  - setup_llvm_minimal_build(): sets up llvm_tarball_* repos needed by genrule build targets
  - llvm_toolchain_alias: repository rule that resolves llvm_toolchain_llvm to the
    matching host-arch llvm_minimal_* repo, or host LLVM tools on Windows

To update the allowlist, edit LLVM_MINIMAL_BINS or LLVM_MINIMAL_LIB_GLOBS below and
rebuild/re-release.
"""

load("//:versions.bzl", "LLVM_DISTRIBUTIONS", "LLVM_VERSION", "VERSIONS")

_TAR_TOOLCHAIN_TYPE = "@aspect_bazel_lib//lib:tar_toolchain_type"

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

# Archive strip prefixes corresponding to each platform tarball.
# Format: "LLVM-{version}-{platform}" (the top-level directory inside the
# upstream release tarballs).
LLVM_TARBALL_STRIP_PREFIXES = {
    "Linux-X64": "LLVM-%s-Linux-X64" % LLVM_VERSION,
    "Linux-ARM64": "LLVM-%s-Linux-ARM64" % LLVM_VERSION,
    "macOS-ARM64": "LLVM-%s-macOS-ARM64" % LLVM_VERSION,
}

# =============================================================================
# Repository rule: LLVM tarball blob (for building minimal artifacts)
# =============================================================================

def _lib_glob_to_extract_spec(pattern):
    """Convert one LLVM_MINIMAL_LIB_GLOBS entry to an extraction match spec."""
    final_segment = pattern.rsplit("/", 1)[-1]
    if "*" in final_segment and "." in final_segment:
        return "glob:" + pattern
    if "*" in pattern:
        return "dir_glob:" + pattern
    return "dir:" + pattern

def _llvm_version_major(version):
    return version.split(".")[0]

def parse_clang_version(stdout):
    """Return a full x.y.z clang version from --version output, or an empty string."""
    marker = "clang version "
    for line in stdout.split("\n"):
        if marker not in line:
            continue
        version = line.split(marker, 1)[1].strip().split(" ")[0].split("-")[0]
        components = version.split(".")
        if len(components) != 3:
            return ""
        for component in components:
            if not component or not component.isdigit():
                return ""
        return version
    return ""

def write_llvm_bzl(repository_ctx, llvm_version, llvm_lib_dir, is_host):
    major = llvm_version.split(".")[0]
    major_minor = ".".join(llvm_version.split(".")[:2])
    repository_ctx.file("llvm.bzl", """\
LLVM_VERSION = %r
LLVM_MAJOR = %r
LLVM_MAJOR_MINOR = %r
LLVM_LIB_DIR = %r
LLVM_IS_HOST = %s
""" % (llvm_version, major, major_minor, llvm_lib_dir, is_host))

# Patterns exported (as individual file labels) by the generated llvm_repo BUILD,
# passed to render_llvm_repo_build() below. The minimal/tarball variant is a clean
# LLVM tree so a broad sweep is safe. The host variant is rooted at a system
# prefix (e.g. /usr), so it is scoped to LLVM files only: a broad "lib/**" sweep
# there also matches non-LLVM files with characters Bazel forbids in target names
# (e.g. ':' in man pages, '\' in systemd unit names), aborting exports_files().
_MINIMAL_EXPORTS_GLOB = [
    "bin/*",
    "lib/**",
    "lib64/**",
    "include/**",
    "share/clang/*",
]

_HOST_EXPORTS_GLOB = [
    "bin/*",
    "lib/clang/**",
    "lib/libclang.so*",
    "lib/libclang-cpp.so*",
    "lib/libLLVM.so*",
    # Debian/Ubuntu multiarch lib dirs (lib/<triple>/), per _detect_llvm_lib_dir.
    "lib/*/libclang.so*",
    "lib/*/libclang-cpp.so*",
    "lib/*/libLLVM.so*",
    "lib64/libclang.so*",
    "lib64/libclang-cpp.so*",
    "lib64/libLLVM.so*",
    "include/clang*/**",
    "include/llvm*/**",
    "include/c++/**",
    "include/*/c++/**",
    "share/clang/*",
]

def render_llvm_repo_build(llvm_major, is_host = False):
    """Render BUILD.llvm_repo-shaped BUILD content for a minimal LLVM artifact.

    Args:
      llvm_major: LLVM major version, used to locate the clang resource dir.
      is_host: Whether the artifact is a host LLVM installation rooted at a
        system prefix (e.g. /usr) instead of a clean minimal tarball. Selects the
        exports_files() glob: _HOST_EXPORTS_GLOB (scoped to LLVM files) vs
        _MINIMAL_EXPORTS_GLOB (broad). See those constants for the rationale.

    Returns:
      The BUILD file content as a string.
    """
    exports_files_glob = _HOST_EXPORTS_GLOB if is_host else _MINIMAL_EXPORTS_GLOB
    return """load("@rules_cc//cc:cc_library.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

exports_files(["llvm.bzl"] + glob({exports_files_glob}, allow_empty = True))

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
    srcs = glob(["lib/**/libclang.so*", "lib/**/libclang*.dylib", "lib64/**/libclang.so*", "lib64/**/libclang*.dylib"], allow_empty = True),
)

filegroup(
    name = "libclang_cpp",
    srcs = glob(["lib/**/libclang-cpp.so*", "lib64/**/libclang-cpp.so*"], allow_empty = True),
)

filegroup(
    name = "libllvm",
    srcs = glob(["lib/**/libLLVM.so*", "lib64/**/libLLVM.so*"], allow_empty = True),
)

cc_library(
    name = "clang_tooling_headers",
    hdrs = glob(["include/clang/**", "include/clang-c/**", "include/llvm/**", "include/llvm-c/**"], allow_empty = True),
    includes = ["include"],
)
""".format(llvm_major = llvm_major, exports_files_glob = exports_files_glob)

LLVM_MINIMAL_LLVM_REPO_BUILD = render_llvm_repo_build(_llvm_version_major(LLVM_VERSION))

# Consumers that supply their own (host) LLVM toolchain and never compile with
# the released minimal LLVM can set this to "1"/"true" to skip the download and
# get an empty placeholder repo instead -- useful for offline/air-gapped builds
# where fetching an unused ~100MB+ artifact would fail or bloat a vendor snapshot.
_SKIP_DOWNLOAD_ENV = "ENVOY_TOOLSHED_SKIP_LLVM_MINIMAL_DOWNLOAD"

def _skip_llvm_minimal_download(ctx):
    return ctx.getenv(_SKIP_DOWNLOAD_ENV) in ("1", "true", "True")

def _llvm_minimal_repo_impl(ctx):
    """Downloads and extracts a released minimal LLVM artifact."""
    if ctx.attr.sha256 and not _skip_llvm_minimal_download(ctx):
        ctx.download_and_extract(
            url = ctx.attr.url,
            sha256 = ctx.attr.sha256,
            stripPrefix = ctx.attr.strip_prefix,
        )
    else:
        # Empty placeholder repo -- used before the first release (sha256 unset)
        # and when a consumer opts out of the download via _SKIP_DOWNLOAD_ENV --
        # so callers that do not reference it are not broken.
        result = ctx.execute(["mkdir", "-p", "bin", "include", "lib", "share/clang"])
        if result.return_code:
            fail("Failed to create placeholder llvm_minimal repo directories: " + result.stderr)
    ctx.file("BUILD.bazel", LLVM_MINIMAL_LLVM_REPO_BUILD)
    write_llvm_bzl(ctx, LLVM_VERSION, "lib", False)

llvm_minimal_repo = repository_rule(
    implementation = _llvm_minimal_repo_impl,
    environ = [_SKIP_DOWNLOAD_ENV],
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
    """Downloads an upstream LLVM tarball as an opaque blob.

    The tarball is NOT extracted here; extraction happens inside the actions
    that consume it.  This means the action key for those actions is a single
    blob digest (computable instantly from the sha256 attribute), so a remote
    cache hit resolves in milliseconds with no extraction cost.
    """
    ctx.download(
        url = ctx.attr.url,
        output = "llvm.tar.xz",
        sha256 = ctx.attr.sha256,
    )
    ctx.file("BUILD.bazel", 'exports_files(["llvm.tar.xz"])\n')
    return ctx.repo_metadata(reproducible = True)

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
            doc = "LLVM version used to compute the archive strip prefix (LLVM-{version}-{platform})",
        ),
        "platform": attr.string(
            mandatory = True,
            doc = "LLVM platform suffix used to compute the archive strip prefix",
        ),
    },
    doc = "Downloads an upstream LLVM tarball as an opaque blob for hermetic in-action extraction.",
)

def _normalize_llvm_toolchain_alias_os(os_name):
    """Normalize repository_ctx.os.name for llvm_toolchain_llvm alias selection."""
    os_name = os_name.lower()
    if os_name.startswith("linux"):
        return "linux"
    if os_name.startswith("mac os x") or os_name.startswith("darwin"):
        return "macos"
    return None

def _normalize_llvm_toolchain_alias_arch(arch):
    """Normalize repository_ctx.os.arch for llvm_toolchain_llvm alias selection."""
    arch = arch.lower()
    if arch.startswith("x86_64") or arch.startswith("amd64"):
        return "x86_64"
    if arch.startswith("aarch64") or arch.startswith("arm64"):
        return "aarch64"
    return None

def _select_llvm_toolchain_alias_label(ctx):
    """Resolve the host platform to the matching minimal repo BUILD.bazel label.

    Selection is by canonical label attribute (populated by the extension that
    owns the llvm_minimal_* repos) rather than a bare apparent-name Label, so
    the repos resolve within the extension's visibility namespace.
    """
    os_name = _normalize_llvm_toolchain_alias_os(ctx.os.name)
    arch = _normalize_llvm_toolchain_alias_arch(ctx.os.arch)

    if os_name == "linux":
        if arch == "x86_64":
            return ctx.attr.minimal_linux_x64
        elif arch == "aarch64":
            return ctx.attr.minimal_linux_arm64

    elif os_name == "macos" and arch == "aarch64":
        # Only macOS ARM64 minimal artifacts are currently published.
        return ctx.attr.minimal_macos_arm64

    fail("Unsupported host platform for llvm_toolchain_llvm alias: {} {}. Supported combinations are linux/x86_64, linux/aarch64, and macos/arm64.".format(ctx.os.name, ctx.os.arch))

def _symlink_dir_children(ctx, source_dir, relpath):
    """Symlink each child of source_dir individually into relpath in this repo.

    A directory symlink (ctx.symlink on the dir itself) is NOT followed by
    Bazel when sourcing individual files for a filegroup src, so bzlmod
    reports "missing input file '...//:bin/llvm-nm'". Symlinking each child as
    its own file/dir symlink makes every entry a real, stageable input.
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

def _detect_llvm_version(repository_ctx, llvm_root, declared_version, clang_name = "bin/clang"):
    clang = llvm_root.get_child(clang_name)
    result = repository_ctx.execute([str(clang), "--version"])
    if result.return_code != 0:
        fail("Could not run %s --version (exit code %s): %s" % (clang, result.return_code, result.stderr))

    version = parse_clang_version(result.stdout)
    if not version:
        fail("Could not parse a full clang version from %s --version output: %s" % (clang, result.stdout))
    if declared_version and declared_version.split(".")[0] != version.split(".")[0]:
        fail(
            "llvm_toolchain_alias_extension.host(llvm_version = %r) does not match the installed clang version %s" %
            (declared_version, version),
        )
    return version

def _detect_llvm_lib_dir(llvm_root, major):
    library_name = "libclang-cpp.so.%s" % major
    for candidate in ["lib", "lib64", "lib/x86_64-linux-gnu", "lib/aarch64-linux-gnu"]:
        directory = llvm_root.get_child(candidate)
        if not directory.exists:
            continue
        for library in directory.readdir():
            if library.basename == library_name or library.basename.startswith(library_name + "."):
                return candidate
    fail("Could not find %s under %s in lib, lib64, lib/x86_64-linux-gnu, or lib/aarch64-linux-gnu" % (library_name, llvm_root))

def _host_llvm_repo_impl(ctx):
    llvm_root = ctx.path(ctx.attr.path)
    version = _detect_llvm_version(ctx, llvm_root, ctx.attr.llvm_version)
    lib_dir = _detect_llvm_lib_dir(llvm_root, version.split(".")[0])
    for directory in ["bin", "include", "lib", "lib64"]:
        path = llvm_root.get_child(directory)
        if not path.exists and directory in ["bin", "include"]:
            fail("Host LLVM directory does not exist: %s" % path)
        if path.exists:
            _symlink_dir_children(ctx, path, directory)
    ctx.file("BUILD.bazel", render_llvm_repo_build(version.split(".")[0], is_host = True))
    write_llvm_bzl(ctx, version, lib_dir, True)

llvm_host_repo = repository_rule(
    implementation = _host_llvm_repo_impl,
    local = True,
    attrs = {
        "path": attr.string(mandatory = True),
        "llvm_version": attr.string(default = ""),
    },
    doc = "Creates a repository backed by a host LLVM installation.",
)

# Host LLVM tools exposed on Windows (clang-cl host toolchain, no hermetic LLVM to alias).
# Keep in sync with direct `@llvm_toolchain_llvm//:<tool>` references in Envoy
# (objcopy: bazel/envoy_binary.bzl; nm/objcopy: dynamic_modules.bzl).
_WINDOWS_LLVM_TOOLS = ["objcopy", "nm"]

def _windows_llvm_repo(ctx):
    llvm_root = ctx.path(
        (ctx.getenv("BAZEL_LLVM") or "C:/Program Files/LLVM").replace("\\", "/").rstrip("/"),
    )
    aliases = []
    for tool in _WINDOWS_LLVM_TOOLS:
        exe = "bin/llvm-%s.exe" % tool
        src = llvm_root.get_child(exe)
        if not src.exists:
            fail("Could not find %s. Set BAZEL_LLVM to the host LLVM installation." % src)
        ctx.symlink(src, exe)
        aliases.append('alias(\n    name = "%s",\n    actual = "%s",\n)\n' % (tool, exe))
    ctx.file("BUILD.bazel", """\
package(default_visibility = ["//visibility:public"])

exports_files(["llvm.bzl"])

""" + "\n".join(aliases))
    version = _detect_llvm_version(ctx, llvm_root, "", "bin/clang.exe")
    write_llvm_bzl(ctx, version, "lib", True)

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

    On Windows, expose objcopy and nm from the host LLVM installation instead.
    """
    if ctx.os.name.lower().startswith("windows"):
        _windows_llvm_repo(ctx)
        return

    minimal_build_label = _select_llvm_toolchain_alias_label(ctx)
    minimal_root = ctx.path(minimal_build_label).dirname

    _ensure_repo_dir(ctx, minimal_root, "bin")
    _ensure_repo_dir(ctx, minimal_root, "include")
    _ensure_repo_dir(ctx, minimal_root, "lib")
    _ensure_repo_dir(ctx, minimal_root, "lib64")

    ctx.file("BUILD.bazel", LLVM_MINIMAL_LLVM_REPO_BUILD)
    write_llvm_bzl(ctx, LLVM_VERSION, "lib", False)

llvm_toolchain_alias = repository_rule(
    implementation = _llvm_toolchain_alias_impl,
    attrs = {
        "minimal_linux_x64": attr.label(
            mandatory = True,
            doc = "BUILD.bazel label of the Linux-X64 minimal LLVM repo.",
        ),
        "minimal_linux_arm64": attr.label(
            mandatory = True,
            doc = "BUILD.bazel label of the Linux-ARM64 minimal LLVM repo.",
        ),
        "minimal_macos_arm64": attr.label(
            mandatory = True,
            doc = "BUILD.bazel label of the macOS-ARM64 minimal LLVM repo.",
        ),
    },
    doc = "Creates the host-arch llvm_toolchain_llvm alias backed by llvm_minimal_* repos.",
)

# =============================================================================
# Build rules: host tool bootstrap, minimal lib extraction, and bin strip
# =============================================================================

# Script: extract LLVM host tools from the Linux-X64 tarball.
# Arguments: BSDTAR TARBALL STRIP_PREFIX OUT_STRIP OUT_READOBJ OUT_READELF OUT_INSTALL_NAME_TOOL
_LLVM_EXTRACT_HOST_TOOLS_SCRIPT = """
set -euo pipefail
BSDTAR="$1"
TARBALL="$2"
STRIP_PREFIX="$3"
OUT_STRIP="$4"
OUT_READOBJ="$5"
OUT_READELF="$6"
OUT_INSTALL_NAME_TOOL="$7"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

"$BSDTAR" xf "$TARBALL" \\
    --strip-components=1 \\
    -C "$SCRATCH" \\
    "$STRIP_PREFIX/bin/llvm-objcopy" \\
    "$STRIP_PREFIX/bin/llvm-strip" \\
    "$STRIP_PREFIX/bin/llvm-readobj" \\
    "$STRIP_PREFIX/bin/llvm-readelf" \\
    "$STRIP_PREFIX/bin/llvm-install-name-tool"
cp -L "$SCRATCH/bin/llvm-strip" "$OUT_STRIP"
cp -L "$SCRATCH/bin/llvm-readobj" "$OUT_READOBJ"
cp -L "$SCRATCH/bin/llvm-readelf" "$OUT_READELF"
cp -L "$SCRATCH/bin/llvm-install-name-tool" "$OUT_INSTALL_NAME_TOOL"
"""

def _llvm_minimal_extract_host_tools_impl(ctx):
    """Extracts LLVM host tools from the Linux-X64 tarball."""
    bsdtar = ctx.toolchains[_TAR_TOOLCHAIN_TYPE]
    tarball = ctx.file.tarball
    strip_prefix = ctx.attr.strip_prefix
    out_strip = ctx.actions.declare_file("llvm_host_tools/llvm-strip")
    out_readobj = ctx.actions.declare_file("llvm_host_tools/llvm-readobj")
    out_readelf = ctx.actions.declare_file("llvm_host_tools/llvm-readelf")
    out_install_name_tool = ctx.actions.declare_file("llvm_host_tools/llvm-install-name-tool")
    ctx.actions.run_shell(
        inputs = [tarball],
        tools = [bsdtar.tarinfo.binary],
        outputs = [out_strip, out_readobj, out_readelf, out_install_name_tool],
        env = bsdtar.tarinfo.default_env,
        command = _LLVM_EXTRACT_HOST_TOOLS_SCRIPT,
        arguments = [
            bsdtar.tarinfo.binary.path,
            tarball.path,
            strip_prefix,
            out_strip.path,
            out_readobj.path,
            out_readelf.path,
            out_install_name_tool.path,
        ],
        mnemonic = "LlvmExtractHostTools",
        progress_message = "Extracting LLVM host tools",
    )
    return [
        DefaultInfo(files = depset([out_strip, out_readobj, out_readelf, out_install_name_tool])),
        OutputGroupInfo(
            llvm_strip = depset([out_strip]),
            llvm_readobj = depset([out_readobj]),
            llvm_readelf = depset([out_readelf]),
            llvm_install_name_tool = depset([out_install_name_tool]),
        ),
    ]

llvm_minimal_extract_host_tools = rule(
    implementation = _llvm_minimal_extract_host_tools_impl,
    attrs = {
        "tarball": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "The Linux-X64 LLVM tarball blob.",
        ),
        "strip_prefix": attr.string(
            mandatory = True,
            doc = "Archive strip prefix (e.g. 'LLVM-22.1.8-Linux-X64').",
        ),
    },
    toolchains = [_TAR_TOOLCHAIN_TYPE],
    doc = "Extracts llvm-strip, llvm-readobj, and llvm-install-name-tool from the Linux-X64 LLVM tarball.",
)

# Script: extract minimal lib/include tree matching LLVM_MINIMAL_LIB_GLOBS patterns.
# Arguments: BSDTAR TARBALL STRIP_PREFIX OUT_DIR [match spec ...]
_LLVM_EXTRACT_LIBS_SCRIPT = """
set -euo pipefail
BSDTAR="$1"
TARBALL="$2"
STRIP_PREFIX="$3"
OUT_DIR="$4"
shift 4
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

match_specs=("$@")
matched_members=()

while IFS= read -r member; do
    rel="${member#"$STRIP_PREFIX"/}"
    if [ "$rel" = "$member" ]; then
        continue
    fi
    for spec in "${match_specs[@]}"; do
        kind="${spec%%:*}"
        pattern="${spec#*:}"
        case "$kind" in
            dir)
                if [ "$rel" = "$pattern" ] || [[ "$rel" == "$pattern"/* ]]; then
                    matched_members+=("$member")
                    break
                fi
                ;;
            dir_glob)
                if [[ "$rel" == $pattern ]] || [[ "$rel" == $pattern/* ]]; then
                    matched_members+=("$member")
                    break
                fi
                ;;
            glob)
                if [[ "$rel" == $pattern ]]; then
                    matched_members+=("$member")
                    break
                fi
                ;;
            *)
                echo "ERROR: unknown LLVM lib extraction spec: $spec" >&2
                exit 1
                ;;
        esac
    done
done < <("$BSDTAR" tf "$TARBALL")

if [ "${#matched_members[@]}" -eq 0 ]; then
    echo "ERROR: no LLVM lib/include members matched the allowlist for $STRIP_PREFIX" >&2
    exit 1
fi

"$BSDTAR" xf "$TARBALL" \\
    --strip-components=1 \\
    -C "$SCRATCH" \\
    "${matched_members[@]}"

require_non_empty_dir() {
    local path="$1"
    local label="$2"
    if [ ! -d "$path" ]; then
        echo "ERROR: expected LLVM $label subtree missing after extraction: $path" >&2
        exit 1
    fi
    local first_entry
    first_entry="$(find "$path" -mindepth 1 -print -quit)"
    if [ -z "$first_entry" ]; then
        echo "ERROR: expected LLVM $label subtree to be non-empty after extraction: $path" >&2
        exit 1
    fi
}

require_non_empty_dir "$SCRATCH/lib" "lib"
require_non_empty_dir "$SCRATCH/include" "include"

# Copy extracted lib/ and include/ subtrees into OUT_DIR.
mkdir -p "$OUT_DIR"
cp -r "$SCRATCH/lib" "$OUT_DIR/"
cp -r "$SCRATCH/include" "$OUT_DIR/"
"""

def _llvm_minimal_extract_libs_impl(ctx):
    """Extracts the minimal lib/include tree from an LLVM tarball blob."""
    bsdtar = ctx.toolchains[_TAR_TOOLCHAIN_TYPE]
    tarball = ctx.file.tarball
    strip_prefix = ctx.attr.strip_prefix
    out_dir = ctx.actions.declare_directory(
        "llvm_minimal_%s_libs_src" % ctx.attr.repo_suffix,
    )

    match_specs = [_lib_glob_to_extract_spec(pattern) for pattern in ctx.attr.lib_globs]

    ctx.actions.run_shell(
        inputs = [tarball],
        tools = [bsdtar.tarinfo.binary],
        outputs = [out_dir],
        env = bsdtar.tarinfo.default_env,
        command = _LLVM_EXTRACT_LIBS_SCRIPT,
        arguments = [bsdtar.tarinfo.binary.path, tarball.path, strip_prefix, out_dir.path] + match_specs,
        mnemonic = "LlvmExtractLibs",
        progress_message = "Extracting LLVM minimal libs for " + ctx.attr.platform,
    )
    return [DefaultInfo(files = depset([out_dir]))]

llvm_minimal_extract_libs = rule(
    implementation = _llvm_minimal_extract_libs_impl,
    attrs = {
        "tarball": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "The LLVM tarball blob.",
        ),
        "strip_prefix": attr.string(
            mandatory = True,
            doc = "Archive strip prefix (e.g. 'LLVM-22.1.8-Linux-X64').",
        ),
        "lib_globs": attr.string_list(
            mandatory = True,
            doc = "LLVM_MINIMAL_LIB_GLOBS entries to extract.",
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
    toolchains = [_TAR_TOOLCHAIN_TYPE],
    doc = "Extracts the minimal lib/include tree from an LLVM tarball blob.",
)

# Three-pass script implementing the intended algorithm:
#   Pass 0 — extract bin/ subtree from the tarball into a scratch directory.
#   Pass 1 — copy EXACTLY the allowlisted files with `cp -P` and no symlink
#            unwrapping or reconstruction. A symlink stays a symlink and a real
#            file stays a real file.
#   Pass 2 — fail loudly on dangling symlinks in DEST before stripping.
#   Pass 3 — walk DEST, skip symlinks and anything that cannot be stripped
#            (probed via llvm-readobj --file-headers), and strip the rest.
#            `find -maxdepth 1 -type f` skips symlinks; the readobj probe skips
#            scripts like git-clang-format that are not valid object files.
#
# Arguments: DEST STRIPPER READOBJ BSDTAR TARBALL STRIP_PREFIX [name ...]
#   name        — allowlisted tool basename (e.g. "clang" or "clang-22")
#
# Tools absent from the tarball's bin/ (e.g. macOS-only tools on a Linux
# tarball) are silently skipped.
_LLVM_STRIP_BINS_SCRIPT = """
set -euo pipefail
DEST="$1"
STRIPPER="$2"
READOBJ="$3"
BSDTAR="$4"
TARBALL="$5"
STRIP_PREFIX="$6"
shift 6
mkdir -p "$DEST"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

# Pass 0: extract only allowlisted bin entries present in the tarball.
extract_members=()
while IFS= read -r member; do
    case "$member" in
        "$STRIP_PREFIX/bin/"*)
            for name in "$@"; do
                if [ "$member" = "$STRIP_PREFIX/bin/$name" ]; then
                    extract_members+=("$member")
                    break
                fi
            done
            ;;
    esac
done < <("$BSDTAR" tf "$TARBALL")

if [ "${#extract_members[@]}" -gt 0 ]; then
    "$BSDTAR" xf "$TARBALL" --strip-components=1 -C "$SCRATCH" "${extract_members[@]}"
fi

# Pass 1: exact copy of allowlisted tools present in the tarball; cp -P never
# dereferences symlinks.
for name in "$@"; do
    src="$SCRATCH/bin/$name"
    if [ -e "$src" ] || [ -L "$src" ]; then
        if [ -L "$src" ]; then
            target="$(readlink "$src")"
            while [ -L "$SCRATCH/bin/$target" ]; do
                target="$(readlink "$SCRATCH/bin/$target")"
            done
            ln -s "$target" "$DEST/$name"
        else
            cp -P "$src" "$DEST/$name"
        fi
    fi
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

    The input is a single tarball blob; the action key is a single blob digest
    computable instantly without any extraction.  A remote cache hit resolves in
    milliseconds and extraction only happens on a genuine cache miss.
    """
    out_dir = ctx.actions.declare_directory(
        "llvm_minimal_%s_bins_src" % ctx.attr.repo_suffix,
    )
    tarball = ctx.file.tarball
    stripper = ctx.file.stripper
    readobj = ctx.file.readobj
    bsdtar = ctx.toolchains[_TAR_TOOLCHAIN_TYPE]

    ctx.actions.run_shell(
        inputs = [tarball],
        # stripper and readobj are declared as tools so Bazel tracks them in the
        # exec configuration and provides their runfiles automatically.
        tools = [stripper, readobj, bsdtar.tarinfo.binary],
        outputs = [out_dir],
        env = bsdtar.tarinfo.default_env,
        command = _LLVM_STRIP_BINS_SCRIPT,
        arguments = [
            out_dir.path + "/bin",
            stripper.path,
            readobj.path,
            bsdtar.tarinfo.binary.path,
            tarball.path,
            ctx.attr.strip_prefix,
        ] + ctx.attr.bins,
        mnemonic = "LlvmMinimalStripBins",
        progress_message = "Stripping LLVM minimal bins for " + ctx.attr.platform,
    )

    return [DefaultInfo(files = depset([out_dir]))]

llvm_minimal_strip_bins = rule(
    implementation = _llvm_minimal_strip_bins_impl,
    attrs = {
        "tarball": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "The LLVM tarball blob (llvm.tar.xz from the llvm_tarball repo).",
        ),
        "strip_prefix": attr.string(
            mandatory = True,
            doc = "Archive strip prefix (e.g. 'LLVM-22.1.8-Linux-X64').",
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
    toolchains = [_TAR_TOOLCHAIN_TYPE],
    doc = "Assembles and strips the minimal LLVM bin/ tree for one platform.",
)

def setup_llvm_minimal_build():
    """Set up llvm_tarball_* repos needed to build the minimal LLVM artifacts.

    Creates three repositories, each containing a single opaque tarball blob:
      @llvm_tarball_linux_x86_64 — Linux-X64 LLVM tarball (llvm.tar.xz)
      @llvm_tarball_linux_arm64  — Linux-ARM64 LLVM tarball (llvm.tar.xz)
      @llvm_tarball_macos_arm64  — macOS-ARM64 LLVM tarball (llvm.tar.xz)

    These are consumed by the //compile:llvm_minimal_* build targets.
    Extraction happens inside the actions that use these repos, not here.
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
