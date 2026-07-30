load("@bazel_skylib//rules:common_settings.bzl", "bool_flag")
load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
load("//:versions.bzl", "LLVM_VERSION", "SUPPORTED_ARCHES", "VERSIONS")
load(":llvm_minimal.bzl", "LLVM_MINIMAL_BINS", "LLVM_MINIMAL_PLATFORMS")

package(default_visibility = ["//visibility:public"])

exports_files(["sanitizer_libs.bzl", "libcxx_libs.bzl", "llvm_minimal.bzl", "extensions.bzl"])

# Build setting to control which toolchain to use
# This can be set with --//compile:use_gcc_toolchain=true
bool_flag(
    name = "use_gcc_toolchain",
    build_setting_default = False,
)

config_setting(
    name = "gcc_build",
    flag_values = {":use_gcc_toolchain": "true"},
)

config_setting(
    name = "macos_build",
    constraint_values = ["@platforms//os:osx"],
)

# LLVM/Clang specific environment variables
LLVM_SANITIZER_ENV = {
    "CXXFLAGS": "-nostdinc++ -nostdlib++",
    "LDFLAGS": "-nostdlib++",
}

# GCC compatible environment (nostdlib++ is Clang-specific)
GCC_SANITIZER_ENV = {
    "CXXFLAGS": "-nostdinc++",
    "LDFLAGS": "",
}

MACOS_SANITIZER_ENV = {
    "CXXFLAGS": "-nostdinc++",
    "LDFLAGS": "",
}

SANITIZER_ENV = select({
    ":gcc_build": GCC_SANITIZER_ENV,
    ":macos_build": MACOS_SANITIZER_ENV,
    "//conditions:default": LLVM_SANITIZER_ENV,
})

# Linker flags that differ between LLVM (lld) and GCC (default linker)
LLVM_LINKER_FLAGS = {
    "LLVM_USE_LINKER": "lld",
    "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
    "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
    "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S -fuse-ld=lld",
}

GCC_LINKER_FLAGS = {
    # Don't specify LLVM_USE_LINKER for GCC, let CMake/compiler choose
    "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S",
    "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S",
    "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S",
}

MACOS_LINKER_FLAGS = {
    "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S",
    "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S",
    "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S",
}

# Base CMake configuration without linker-specific flags
BASE_CMAKE_CACHE_COMMON = {
    "CMAKE_BUILD_TYPE": "RelWithDebInfo",
    "CMAKE_INSTALL_PREFIX": ".",
    "CMAKE_POSITION_INDEPENDENT_CODE": "ON",
    "LLVM_ENABLE_RUNTIMES": "libcxxabi;libcxx;libunwind",
    "BUILD_SHARED_LIBS": "OFF",
    "LIBCXX_ENABLE_SHARED": "OFF",
    "LIBCXX_ENABLE_STATIC": "ON",
    "LIBCXXABI_ENABLE_SHARED": "OFF",
    "LIBCXXABI_ENABLE_STATIC": "ON",
    "LIBUNWIND_ENABLE_SHARED": "OFF",
    "LIBUNWIND_ENABLE_STATIC": "ON",
}

# Merge with linker-specific flags based on toolchain
BASE_CMAKE_CACHE = BASE_CMAKE_CACHE_COMMON | select({
    ":gcc_build": GCC_LINKER_FLAGS,
    ":macos_build": MACOS_LINKER_FLAGS,
    "//conditions:default": LLVM_LINKER_FLAGS,
})

PYTHON_CMAKE_CACHE = {
    "Python3_EXECUTABLE": "$$EXT_BUILD_ROOT/$(PYTHON3)",
}

cmake(
    name = "libcxx_msan",
    cache_entries = BASE_CMAKE_CACHE | PYTHON_CMAKE_CACHE | {
        "LLVM_USE_SANITIZER": "MemoryWithOrigins",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
    ],
    target_compatible_with = select({
        ":gcc_build": ["@platforms//:incompatible"],
        ":macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    toolchains = ["@rules_python//python:current_py_toolchain"],
    working_directory = "runtimes",
)

cmake(
    name = "libcxx_tsan",
    cache_entries = BASE_CMAKE_CACHE | PYTHON_CMAKE_CACHE | {
        "LLVM_USE_SANITIZER": "Thread",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
    ],
    target_compatible_with = select({
        ":gcc_build": ["@platforms//:incompatible"],
        ":macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    toolchains = ["@rules_python//python:current_py_toolchain"],
    working_directory = "runtimes",
)

pkg_files(
    name = "msan_libs_files",
    srcs = [":libcxx_msan"],
    target_compatible_with = select({
        ":gcc_build": ["@platforms//:incompatible"],
        ":macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    excludes = [
        "**/*.h",
        "**/include/**",
    ],
    prefix = "msan-libs-x86_64/lib",
    strip_prefix = ".",
)

pkg_tar(
    name = "cxx_msan",
    target_compatible_with = select({
        ":gcc_build": ["@platforms//:incompatible"],
        ":macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    srcs = [":msan_libs_files"],
    extension = "tar.xz",
    package_file_name = "msan-llvm%s-x86_64.tar.xz" % VERSIONS["llvm"],
)

pkg_files(
    name = "tsan_libs_files",
    target_compatible_with = select({
        ":gcc_build": ["@platforms//:incompatible"],
        ":macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    srcs = [":libcxx_tsan"],
    excludes = [
        "**/*.h",
        "**/include/**",
    ],
    prefix = "tsan-libs-x86_64/lib",
    strip_prefix = ".",
)

pkg_tar(
    name = "cxx_tsan",
    srcs = [":tsan_libs_files"],
    extension = "tar.xz",
    package_file_name = "tsan-llvm%s-x86_64.tar.xz" % VERSIONS["llvm"],
    target_compatible_with = select({
        ":gcc_build": ["@platforms//:incompatible"],
        ":macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
)

[
    (
        pkg_files(
            name = "libcxx_%s_lib_files" % arch,
            srcs = [
                "@llvm_libcxx_%s//:libcxx" % arch,
            ],
            prefix = "lib",
            strip_prefix = ".",
            target_compatible_with = select({
                ":gcc_build": ["@platforms//:incompatible"],
                ":macos_build": ["@platforms//:incompatible"],
                "//conditions:default": [],
            }),
        ),
        pkg_files(
            name = "libcxx_%s_compiler_rt_files" % arch,
            srcs = [
                "@llvm_libcxx_%s//:compiler_rt" % arch,
            ],
            prefix = "lib",
            strip_prefix = ".",
            target_compatible_with = select({
                ":gcc_build": ["@platforms//:incompatible"],
                ":macos_build": ["@platforms//:incompatible"],
                "//conditions:default": [],
            }),
        ),
        pkg_files(
            name = "libcxx_%s_include_files" % arch,
            srcs = [
                "@llvm_libcxx_%s//:config_site" % arch,
            ],
            prefix = "include",
            strip_prefix = ".",
            target_compatible_with = select({
                ":gcc_build": ["@platforms//:incompatible"],
                ":macos_build": ["@platforms//:incompatible"],
                "//conditions:default": [],
            }),
        ),
        pkg_tar(
            name = "libcxx_%s" % arch,
            srcs = [
                ":libcxx_%s_lib_files" % arch,
                ":libcxx_%s_compiler_rt_files" % arch,
                ":libcxx_%s_include_files" % arch,
            ],
            extension = "tar.xz",
            package_file_name = "libcxx-llvm%s-%s.tar.xz" % (VERSIONS["llvm"], arch),
            target_compatible_with = select({
                ":gcc_build": ["@platforms//:incompatible"],
                ":macos_build": ["@platforms//:incompatible"],
                "//conditions:default": [],
            }),
        ),
    )
    for arch in SUPPORTED_ARCHES
]

# =============================================================================
# Minimal LLVM extraction targets
#
# These genrule targets take the upstream LLVM release tarballs (downloaded via
# llvm_tarball_* repository rules) and produce stripped, minimal .tar.xz
# artifacts containing only the tools and libraries in the allowlist defined in
# llvm_minimal.bzl.
#
# Build all three platforms:
#   bazel build //compile:llvm_minimal_linux_x86_64
#   bazel build //compile:llvm_minimal_linux_arm64
#   bazel build //compile:llvm_minimal_macos_arm64
#
# Prerequisites: the llvm_tarball_* repos must be available (see
# setup_llvm_minimal_build() in llvm_minimal.bzl, wired via
# llvm_minimal_build_extension in extensions.bzl).
# =============================================================================

# Extraction script template.  Uses sentinel tokens (replaced via .replace())
# so that shell ${var} syntax does not conflict with any template mechanism.
# $$-escaping is required for Bazel genrule cmd (each $$ becomes $ in the shell).
_LLVM_MINIMAL_EXTRACT_CMD = """
set -euo pipefail
TARBALL=$<
OUTFILE=$@
PLATFORM="__PLATFORM__"
VERSION="__VERSION__"
STRIP_PREFIX="LLVM-__VERSION__-__PLATFORM__"

WORK=$$(mktemp -d)
trap "rm -rf $$WORK" EXIT

# ---------------------------------------------------------------------------
# 1. Extract upstream LLVM tarball
# ---------------------------------------------------------------------------
echo "Extracting $$STRIP_PREFIX ..."
tar xf "$$TARBALL" -C "$$WORK"
SRC="$$WORK/$$STRIP_PREFIX"
OUT_NAME="llvm-minimal-$$VERSION-$$PLATFORM"
DEST="$$WORK/out/$$OUT_NAME"
mkdir -p "$$DEST/bin" "$$DEST/lib" "$$DEST/include"

# ---------------------------------------------------------------------------
# 2. Copy bin/ tools (preserving symlinks so clang/lld are not duplicated)
# ---------------------------------------------------------------------------
for tool in __BINS__; do
    src="$$SRC/bin/$$tool"
    if [ -L "$$src" ]; then
        # Symlink: preserve as-is (cp -P keeps the symlink, not the target)
        cp -P "$$src" "$$DEST/bin/" 2>/dev/null || true
    elif [ -f "$$src" ]; then
        cp "$$src" "$$DEST/bin/"
    fi
done

# ---------------------------------------------------------------------------
# 3. Strip non-symlink binaries / shared objects (best-effort, never fatal)
#    ELF  -> strip --strip-unneeded
#    Mach-O -> strip -x  (native on macOS; may be skipped on Linux cross, ok)
# ---------------------------------------------------------------------------
for f in "$$DEST/bin/"*; do
    [ -L "$$f" ] && continue
    [ -f "$$f" ] || continue
    ftype=$$(file "$$f" 2>/dev/null || echo "unknown")
    if echo "$$ftype" | grep -q "ELF"; then
        strip --strip-unneeded "$$f" 2>/dev/null || true
    elif echo "$$ftype" | grep -q "Mach-O"; then
        strip -x "$$f" 2>/dev/null || true
    fi
done

# ---------------------------------------------------------------------------
# 4. Copy lib/clang/{ver}/{include,lib,share} in full
#    Keeps builtin headers, compiler-rt runtimes, sanitizer ignorelists.
# ---------------------------------------------------------------------------
if [ -d "$$SRC/lib/clang" ]; then
    mkdir -p "$$DEST/lib/clang"
    for clang_ver_dir in "$$SRC/lib/clang"/*/; do
        [ -d "$$clang_ver_dir" ] || continue
        ver=$$(basename "$$clang_ver_dir")
        mkdir -p "$$DEST/lib/clang/$$ver"
        for subdir in include lib share; do
            if [ -d "$${clang_ver_dir}$${subdir}" ]; then
                cp -r "$${clang_ver_dir}$${subdir}" "$$DEST/lib/clang/$$ver/"
            fi
        done
    done
fi

# ---------------------------------------------------------------------------
# 5. Copy include/c++ (libc++ headers)
# ---------------------------------------------------------------------------
if [ -d "$$SRC/include/c++" ]; then
    cp -r "$$SRC/include/c++" "$$DEST/include/"
fi

# ---------------------------------------------------------------------------
# 6. Copy per-triple include/{triple}/c++/v1/__config_site
# ---------------------------------------------------------------------------
if [ -d "$$SRC/include" ]; then
    find "$$SRC/include" -path "*/c++/v1/__config_site" | while IFS= read -r f; do
        case "$$f" in "$${SRC}/include/c++/"*) continue ;; esac
        relpath="$${f#$${SRC}/}"
        mkdir -p "$$DEST/$$(dirname "$$relpath")"
        cp "$$f" "$$DEST/$$relpath"
    done
fi

# ---------------------------------------------------------------------------
# 7. Copy lib/ static archives: libc++*.a, libc++abi*.a, libunwind*.a
# ---------------------------------------------------------------------------
find "$$SRC/lib" \\( -name "libc++*.a" -o -name "libunwind*.a" \\) | while IFS= read -r f; do
    relpath="$${f#$${SRC}/}"
    mkdir -p "$$DEST/$$(dirname "$$relpath")"
    cp "$$f" "$$DEST/$$relpath"
done

# ---------------------------------------------------------------------------
# 8. Copy lib/ shared libunwind (so* / dylib)
# ---------------------------------------------------------------------------
find "$$SRC/lib" \\( -name "libunwind*.so*" -o -name "libunwind*.dylib" \\) 2>/dev/null | while IFS= read -r f; do
    relpath="$${f#$${SRC}/}"
    mkdir -p "$$DEST/$$(dirname "$$relpath")"
    cp -P "$$f" "$$DEST/$$relpath"
done

# ---------------------------------------------------------------------------
# 9. Copy lib/libclang-cpp.so.* or lib/libclang-cpp*.dylib
# ---------------------------------------------------------------------------
find "$$SRC/lib" -maxdepth 1 \\( -name "libclang-cpp.so*" -o -name "libclang-cpp*.dylib" \\) 2>/dev/null | while IFS= read -r f; do
    relpath="$${f#$${SRC}/}"
    cp -P "$$f" "$$DEST/$$relpath"
done

# ---------------------------------------------------------------------------
# 10. Pack minimal tarball
# ---------------------------------------------------------------------------
echo "Creating llvm-minimal-$$VERSION-$$PLATFORM.tar.xz ..."
tar -c -C "$$WORK/out" "$$OUT_NAME" | xz -T0 > "$$OUTFILE"
echo "Done. Output: $$OUTFILE"
"""

[
    genrule(
        name = "llvm_minimal_%s" % repo_suffix,
        srcs = ["@llvm_tarball_%s//:%s" % (repo_suffix, tarball_filename)],
        outs = ["llvm-minimal-%s-%s.tar.xz" % (LLVM_VERSION, platform)],
        cmd = (
            _LLVM_MINIMAL_EXTRACT_CMD
                .replace("__PLATFORM__", platform)
                .replace("__VERSION__", LLVM_VERSION)
                .replace("__BINS__", " ".join(LLVM_MINIMAL_BINS))
        ),
        message = "Building minimal LLVM for %s" % platform,
    )
    for platform, tarball_filename, repo_suffix in [
        ("Linux-X64", LLVM_MINIMAL_PLATFORMS["Linux-X64"], "linux_x86_64"),
        ("Linux-ARM64", LLVM_MINIMAL_PLATFORMS["Linux-ARM64"], "linux_arm64"),
        ("macOS-ARM64", LLVM_MINIMAL_PLATFORMS["macOS-ARM64"], "macos_arm64"),
    ]
]
