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

# Fixed-name LLVM tool filegroups rendered into every minimal/host LLVM repo, as
# (target name, fixed bin/ srcs, extra glob-with-allow_empty patterns).
#
# On the hermetic path the fixed srcs are emitted as literal file labels: the
# minimal artifact is built from this same allowlist (see LLVM_MINIMAL_BINS), so
# a tool missing from the artifact is a genuine integrity error and should fail
# loudly. On the host path (tools_optional = True) the fixed srcs are wrapped in
# glob(..., allow_empty = True) instead, because a distro LLVM is not guaranteed
# to ship every allowlisted tool (e.g. git-clang-format, llvm-dwp, ld64.lld); a
# missing one then yields an empty filegroup rather than a hard "missing input
# file" analysis error for consumers that never reference it.
_LLVM_REPO_TOOL_FILEGROUPS = [
    ("clang", ["bin/clang", "bin/clang++", "bin/clang-cpp"], []),
    ("ld", ["bin/ld.lld", "bin/ld64.lld"], ["bin/wasm-ld"]),
    ("ar", ["bin/llvm-ar"], []),
    ("as", ["bin/clang", "bin/llvm-as"], []),
    ("nm", ["bin/llvm-nm"], []),
    ("objcopy", ["bin/llvm-objcopy"], []),
    ("objdump", ["bin/llvm-objdump"], []),
    ("profdata", ["bin/llvm-profdata"], []),
    ("dwp", ["bin/llvm-dwp"], []),
    ("ranlib", ["bin/llvm-ranlib"], []),
    ("readelf", ["bin/llvm-readelf"], []),
    ("strip", ["bin/llvm-strip"], []),
    ("symbolizer", ["bin/llvm-symbolizer"], []),
    ("clang-tidy", ["bin/clang-tidy"], []),
    ("clang-format", ["bin/clang-format"], []),
    ("git-clang-format", ["bin/git-clang-format"], []),
]

def _render_llvm_tool_filegroups(tools_optional):
    """Render the fixed-name LLVM tool filegroups (see _LLVM_REPO_TOOL_FILEGROUPS)."""
    chunks = []
    for name, fixed, extra_globs in _LLVM_REPO_TOOL_FILEGROUPS:
        if tools_optional:
            srcs = "glob({}, allow_empty = True)".format(fixed)
        else:
            srcs = "{}".format(fixed)
        for pattern in extra_globs:
            srcs += " + glob({}, allow_empty = True)".format([pattern])
        chunks.append("filegroup(\n    name = \"{}\",\n    srcs = {},\n)".format(name, srcs))
    return "\n\n".join(chunks)

def render_llvm_repo_build(llvm_major, tools_optional = False):
    """Render BUILD.llvm_repo-shaped BUILD content for a minimal LLVM artifact.

    When tools_optional is True (the host-LLVM path), the fixed-name tool
    filegroups tolerate tools the host does not ship; see
    _LLVM_REPO_TOOL_FILEGROUPS.
    """
    return """package(default_visibility = ["//visibility:public"])

exports_files(glob(["bin/*", "lib/**", "lib64/**", "include/**", "share/clang/*"], allow_empty = True))

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
        "include/c++/**",
        "lib/clang/{llvm_major}/include/**",
        "lib/clang/{llvm_major}/share/**",
        "lib/clang/{llvm_major}/libcxx-msan/include/**",
        "lib/clang/{llvm_major}/libcxx-msan/source/include/**",
    ], allow_empty = True),
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

{tool_filegroups}

filegroup(
    name = "libclang",
    srcs = glob(["lib/libclang.so*", "lib/libclang*.dylib"], allow_empty = True),
)
""".format(llvm_major = llvm_major, tool_filegroups = _render_llvm_tool_filegroups(tools_optional))

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
    # Only macOS ARM64 minimal artifacts are currently published.
    elif os_name == "macos" and arch == "aarch64":
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

# Environment variable that, when set to a host LLVM install prefix (e.g.
# "/usr"), makes llvm_toolchain_alias back @llvm_toolchain_llvm with that host
# toolchain instead of the hermetic minimal artifact. This is the same variable
# Envoy's own bazel/repo.bzl reads to switch to a host LLVM, so a single knob
# selects the host toolchain consistently across the build.
_HOST_LLVM_PATH_ENV = "BAZEL_LLVM_PATH"

# Subdirectories of a host LLVM's include/ that hold the libclang / libTooling /
# LLVM C++ API headers consumed by downstream tools (e.g. the Envoy openssl
# prefixer, which #includes "clang/AST/...", "clang-c/...", and "llvm/..."). This
# mirrors the include/* entries of LLVM_MINIMAL_LIB_GLOBS so a host LLVM presents
# the same header surface as the hermetic minimal artifact -- and stays scoped to
# LLVM headers rather than sweeping in the whole distro include tree.
_HOST_LLVM_INCLUDE_SUBDIRS = [
    "c++",
    "clang",
    "clang-c",
    "llvm",
    "llvm-c",
]

# Shared-library basename prefixes to expose from a host LLVM's lib/ and lib64/.
# Matches the lib/libclang-cpp.so* / lib/libLLVM.so* / lib/libclang.so* entries
# of LLVM_MINIMAL_LIB_GLOBS.
_HOST_LLVM_SHARED_LIB_PREFIXES = [
    "libclang-cpp.so",
    "libLLVM.so",
    "libclang.so",
]

def _host_llvm_resource_dir(ctx, host_root):
    """Locate a host LLVM's clang resource dir (lib{,64}/clang/<major>).

    Distros place it under lib/ or lib64/; returns (major, path) for the highest
    version found, or (None, None) if absent. The major drives the shared BUILD
    template's lib/clang/<major>/... globs and the bin/ version-suffix probe.
    """
    best_major = None
    best_dir = None
    for libdir in ["lib", "lib64"]:
        clang_root = host_root.get_child(libdir).get_child("clang")
        if not clang_root.exists:
            continue
        for child in clang_root.readdir():
            # Resource dirs are named by version (e.g. "21" or "21.1.8"); compare
            # by the leading integer major so the newest wins deterministically.
            major = child.basename.split(".")[0]
            if not major.isdigit():
                continue
            if best_major == None or int(major) > int(best_major):
                best_major = major
                best_dir = child
    return best_major, best_dir

def _host_llvm_shared_libs(host_root):
    """Collect a host LLVM's shared libraries as {basename: host path}.

    Scans both lib/ and lib64/ (distros differ) and keeps the first occurrence of
    each basename, so callers can place every lib deterministically regardless of
    which dir the host uses. lib64/ is scanned first so that on a 64-bit multilib
    host (e.g. clang-libs.i686 alongside the 64-bit package, which puts a 32-bit
    libclang-cpp.so in /usr/lib and the 64-bit one in /usr/lib64) the 64-bit lib
    wins -- and so the choice matches the lib dir Envoy's repo.bzl probes first
    when it composes the version-qualified label.
    """
    found = {}
    for libdir in ["lib64", "lib"]:
        host_lib_dir = host_root.get_child(libdir)
        if not host_lib_dir.exists:
            continue
        for child in host_lib_dir.readdir():
            for prefix in _HOST_LLVM_SHARED_LIB_PREFIXES:
                if child.basename.startswith(prefix) and child.basename not in found:
                    found[child.basename] = child
                    break
    return found

def _symlink_host_llvm_bins(ctx, host_bin_dir, major):
    """Symlink the allowlisted LLVM tools from a host bin/ dir into bin/.

    Distros ship these version-suffixed (llvm-nm-21) or unversioned (llvm-nm);
    accept whichever exists. The version-suffixed name is preferred so that on a
    host with several LLVMs installed the tools match the resource-dir `major`
    selected by _host_llvm_resource_dir rather than whatever an unversioned
    /usr/bin/clang happens to point at. Tools absent from the host (e.g.
    macOS-only tools) are skipped; the host BUILD renders tool filegroups with
    allow_empty (tools_optional), so a missing optional tool is tolerated.
    """
    if not host_bin_dir.exists:
        return
    for tool in LLVM_MINIMAL_BINS:
        for candidate in ["{}-{}".format(tool, major), tool]:
            src = host_bin_dir.get_child(candidate)
            if src.exists:
                ctx.symlink(src, "bin/{}".format(tool))
                break

def _setup_host_llvm_alias(ctx, host_llvm_path):
    """Back the alias repo with a host LLVM install rooted at host_llvm_path.

    Reproduces the pre-Bzlmod behavior of building against a host (distro) LLVM
    instead of the hermetic minimal artifact. The repo is populated from the host
    -- bin/ tools, the LLVM C++ API headers, the clang resource dir, and the
    libclang / libLLVM shared libraries -- and uses the *same* BUILD template as
    the hermetic path (render_llvm_repo_build), so the host and hermetic aliases
    expose an identical target surface to consumers. The repo name is unchanged,
    so consumers that reference this repo's canonical path (e.g. a hardcoded
    -isystem) keep resolving -- now to the host toolchain.

    Per-child (not whole-directory) symlinks are used, matching the hermetic path,
    because Bazel does not follow a symlinked package directory when sourcing
    individual filegroup inputs.
    """
    host_root = ctx.path(host_llvm_path)
    if not host_root.exists:
        fail("{}='{}' does not exist. Set it to a host LLVM install prefix (e.g. /usr).".format(
            _HOST_LLVM_PATH_ENV,
            host_llvm_path,
        ))

    # The clang resource dir both supplies the builtin headers and pins the LLVM
    # major used below; its absence means this is not a usable LLVM install, so
    # fail fast rather than emit an empty-but-"successful" repo (every glob is
    # allow_empty, so nothing else would complain).
    major, resource_dir = _host_llvm_resource_dir(ctx, host_root)
    if not major:
        fail(("{}='{}' does not look like an LLVM install: no clang resource dir " +
              "found under lib/clang/<major> or lib64/clang/<major>.").format(
            _HOST_LLVM_PATH_ENV,
            host_llvm_path,
        ))

    # LLVM C++ API headers (include/clang, include/llvm, include/c++, ...).
    host_include = host_root.get_child("include")
    for subdir in _HOST_LLVM_INCLUDE_SUBDIRS:
        child = host_include.get_child(subdir)
        if child.exists:
            ctx.symlink(child, "include/{}".format(subdir))

    # Per-target-triple libc++ headers (include/<triple>/c++, which carry
    # v1/__config_site) when the host ships them -- mirrors include/*/c++ in
    # LLVM_MINIMAL_LIB_GLOBS and keeps :extra_config_site resolvable.
    if host_include.exists:
        for child in host_include.readdir():
            triple_cxx = child.get_child("c++")
            if triple_cxx.exists:
                ctx.symlink(triple_cxx, "include/{}/c++".format(child.basename))

    # clang resource-dir builtin headers + runtimes, normalized to
    # lib/clang/<major> so the shared BUILD template's lib/clang/<major>/... globs
    # resolve regardless of whether the host keeps them under lib/ or lib64/.
    for child in resource_dir.readdir():
        ctx.symlink(child, "lib/clang/{}/{}".format(major, child.basename))

    # libclang-cpp / libLLVM / libclang shared libraries. Expose each under both
    # lib/ and lib64/ regardless of which the host uses: lib/ feeds the shared
    # template's lib-globbed filegroups (:libclang, :lib), while lib64/ feeds the
    # version-qualified label Envoy composes from the host's own lib dir (its
    # repo.bzl probes /usr/lib64 first on Fedora/RHEL, yielding
    # @llvm_toolchain_llvm//:lib64/libclang-cpp.so.<ver>).
    for basename, src in _host_llvm_shared_libs(host_root).items():
        ctx.symlink(src, "lib/{}".format(basename))
        ctx.symlink(src, "lib64/{}".format(basename))

    # LLVM bin tools (llvm-nm, llvm-readelf, clang, ...).
    _symlink_host_llvm_bins(ctx, host_root.get_child("bin"), major)

    ctx.file("BUILD.bazel", render_llvm_repo_build(major, tools_optional = True))

def _llvm_toolchain_alias_impl(ctx):
    """Create a host-arch alias repo backed by the matching minimal LLVM artifact.

    When BAZEL_LLVM_PATH is set, the repo is instead backed by that host LLVM
    install (see _setup_host_llvm_alias) -- restoring the ability, lost in the
    WORKSPACE->Bzlmod migration, to build against a distro LLVM rather than the
    hermetic minimal artifact.

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
    host_llvm_path = ctx.os.environ.get(_HOST_LLVM_PATH_ENV, "")
    if host_llvm_path:
        _setup_host_llvm_alias(ctx, host_llvm_path)
        return

    minimal_build_label = _select_llvm_toolchain_alias_label(ctx)
    minimal_root = ctx.path(minimal_build_label).dirname

    _ensure_repo_dir(ctx, minimal_root, "bin")
    _ensure_repo_dir(ctx, minimal_root, "include")
    _ensure_repo_dir(ctx, minimal_root, "lib")

    ctx.file("BUILD.bazel", LLVM_MINIMAL_LLVM_REPO_BUILD)

llvm_toolchain_alias = repository_rule(
    implementation = _llvm_toolchain_alias_impl,
    environ = [_HOST_LLVM_PATH_ENV],
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
