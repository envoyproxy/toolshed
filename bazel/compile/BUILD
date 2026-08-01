load("@aspect_bazel_lib//lib:tar.bzl", "mtree_mutate", "mtree_spec", "tar")
load("@bazel_skylib//rules:common_settings.bzl", "bool_flag")
load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "strip_prefix")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//:versions.bzl", "LLVM_VERSION", "SUPPORTED_ARCHES", "VERSIONS")
load(":llvm_minimal.bzl", "LLVM_MINIMAL_BINS", "LLVM_MINIMAL_LIB_GLOBS", "LLVM_MINIMAL_LLVM_REPO_BUILD", "llvm_minimal_strip_bins")

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
# =============================================================================

_LLVM_MINIMAL_MACOS_ONLY_BINS = [
    "llvm-libtool-darwin",
    "llvm-install-name-tool",
]

_LLVM_MINIMAL_LLVM_MAJOR = LLVM_VERSION.split(".")[0]

# Use llvm-strip/llvm-readobj from the upstream Linux-X64 build tarball when
# producing all minimal artifact variants. This preserves the intended
# bootstrapping flow: strip the minimal artifacts with tools from the full
# upstream tarball, not from the minimal artifact alias.
_LLVM_MINIMAL_HOST_STRIPPER = "@llvm_tarball_linux_x86_64//:bin/llvm-strip"
_LLVM_MINIMAL_HOST_READOBJ = "@llvm_tarball_linux_x86_64//:bin/llvm-readobj"

[
    (
        llvm_minimal_strip_bins(
            name = "llvm_minimal_%s_strip_bins" % repo_suffix,
            bin_all = "@llvm_tarball_%s//:bin_all" % repo_suffix,
            bins = bins,
            stripper = _LLVM_MINIMAL_HOST_STRIPPER,
            readobj = _LLVM_MINIMAL_HOST_READOBJ,
            repo_suffix = repo_suffix,
            platform = platform,
            tags = ["manual"],
        ),
        mtree_spec(
            name = "llvm_minimal_%s_bins_mtree_src" % repo_suffix,
            srcs = [":llvm_minimal_%s_strip_bins" % repo_suffix],
            tags = ["manual"],
        ),
        mtree_mutate(
            name = "llvm_minimal_%s_bins_mtree" % repo_suffix,
            mtree = ":llvm_minimal_%s_bins_mtree_src" % repo_suffix,
            preserve_symlinks = False,
            srcs = [":llvm_minimal_%s_strip_bins" % repo_suffix],
            package_dir = "llvm-minimal-%s-%s" % (LLVM_VERSION, platform),
            strip_prefix = "compile/llvm_minimal_%s_bins_src" % repo_suffix,
            tags = ["manual"],
        ),
        mtree_spec(
            name = "llvm_minimal_%s_libs_mtree_src" % repo_suffix,
            srcs = ["@llvm_tarball_%s//:minimal_libs" % repo_suffix],
            tags = ["manual"],
        ),
        mtree_mutate(
            name = "llvm_minimal_%s_libs_mtree" % repo_suffix,
            mtree = ":llvm_minimal_%s_libs_mtree_src" % repo_suffix,
            package_dir = "llvm-minimal-%s-%s" % (LLVM_VERSION, platform),
            tags = ["manual"],
        ),
        genrule(
            name = "llvm_minimal_%s_build_bazel" % repo_suffix,
            outs = ["llvm_minimal_%s/BUILD.bazel" % repo_suffix],
            cmd = """cat >"$@" <<'EOF'
%s
EOF""" % LLVM_MINIMAL_LLVM_REPO_BUILD,
            tags = ["manual"],
        ),
        mtree_spec(
            name = "llvm_minimal_%s_build_mtree_src" % repo_suffix,
            srcs = [":llvm_minimal_%s_build_bazel" % repo_suffix],
            tags = ["manual"],
        ),
        mtree_mutate(
            name = "llvm_minimal_%s_build_mtree" % repo_suffix,
            mtree = ":llvm_minimal_%s_build_mtree_src" % repo_suffix,
            package_dir = "llvm-minimal-%s-%s" % (LLVM_VERSION, platform),
            strip_prefix = "compile/llvm_minimal_%s" % repo_suffix,
            tags = ["manual"],
        ),
        genrule(
            name = "llvm_minimal_%s_mtree" % repo_suffix,
            srcs = [
                ":llvm_minimal_%s_bins_mtree" % repo_suffix,
                ":llvm_minimal_%s_libs_mtree" % repo_suffix,
                ":llvm_minimal_%s_build_mtree" % repo_suffix,
            ],
            outs = ["llvm_minimal_%s.mtree" % repo_suffix],
            cmd = "cat $(SRCS) > $@",
            tags = ["manual"],
        ),
        tar(
            name = "llvm_minimal_%s" % repo_suffix,
            args = ["--options=zstd:compression-level=19,zstd:threads=4"],
            compress = "zstd",
            exec_properties = {"Pool": "linux_x64_xlarge"},
            mtree = ":llvm_minimal_%s_mtree" % repo_suffix,
            out = "llvm-minimal-%s-%s.tar.zst" % (LLVM_VERSION, platform),
            srcs = [
                ":llvm_minimal_%s_strip_bins" % repo_suffix,
                "@llvm_tarball_%s//:minimal_libs" % repo_suffix,
                ":llvm_minimal_%s_build_bazel" % repo_suffix,
            ],
            tags = ["manual"],
        ),
    )
    for platform, repo_suffix, bins in [
        (
            "Linux-X64",
            "linux_x86_64",
            [b for b in LLVM_MINIMAL_BINS if b not in _LLVM_MINIMAL_MACOS_ONLY_BINS],
        ),
        (
            "Linux-ARM64",
            "linux_arm64",
            [b for b in LLVM_MINIMAL_BINS if b not in _LLVM_MINIMAL_MACOS_ONLY_BINS],
        ),
        (
            "macOS-ARM64",
            "macos_arm64",
            LLVM_MINIMAL_BINS,
        ),
    ]
]

[
    sh_test(
        name = "llvm_minimal_%s_manifest_test" % repo_suffix,
        size = "small",
        srcs = ["//compile/test:assert_llvm_minimal_manifest.sh"],
        data = [":llvm_minimal_%s_mtree" % repo_suffix],
        env = {
            "MTREE": "$(rootpath :llvm_minimal_%s_mtree)" % repo_suffix,
            "PLATFORM": platform,
            "LLVM_MAJOR": _LLVM_MINIMAL_LLVM_MAJOR,
            "BINS": ",".join(bins),
            "LIB_GLOBS": ",".join(LLVM_MINIMAL_LIB_GLOBS),
        },
        tags = ["manual"],
    )
    for platform, repo_suffix, bins in [
        (
            "Linux-X64",
            "linux_x86_64",
            [b for b in LLVM_MINIMAL_BINS if b not in _LLVM_MINIMAL_MACOS_ONLY_BINS],
        ),
        (
            "Linux-ARM64",
            "linux_arm64",
            [b for b in LLVM_MINIMAL_BINS if b not in _LLVM_MINIMAL_MACOS_ONLY_BINS],
        ),
        (
            "macOS-ARM64",
            "macos_arm64",
            LLVM_MINIMAL_BINS,
        ),
    ]
]

sh_test(
    name = "llvm_minimal_linux_x86_64_bins_layout_test",
    size = "small",
    srcs = ["//compile/test:assert_llvm_minimal_bins_layout.sh"],
    data = [":llvm_minimal_linux_x86_64"],
    env = {
        "CLANG_REAL": "clang-%s" % _LLVM_MINIMAL_LLVM_MAJOR,
        "TARBALL": "$(rootpath :llvm_minimal_linux_x86_64)",
        "ROOT_DIR": "llvm-minimal-%s-Linux-X64" % LLVM_VERSION,
    },
    tags = ["manual"],
)
