load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
load("//:versions.bzl", "VERSIONS")

package(default_visibility = ["//visibility:public"])

exports_files(["libcxx_cross.bzl", "extensions.bzl"])

# Reuse the toolchain config settings from //compile rather than defining
# a separate bool_flag. The gcc config in .bazelrc sets
# --//compile:use_gcc_toolchain=true which is sufficient.
CROSS_ENV = select({
    "//compile:gcc_build": {
        "CXXFLAGS": "-nostdinc++",
        "LDFLAGS": "",
    },
    "//compile:macos_build": {
        "CXXFLAGS": "-nostdinc++",
        "LDFLAGS": "",
    },
    "//conditions:default": {
        "CXXFLAGS": "-nostdinc++ -nostdlib++",
        "LDFLAGS": "-nostdlib++",
    },
})

# Common cmake cache entries for cross-compiled LLVM runtimes.
CROSS_CMAKE_CACHE_COMMON = {
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

CROSS_CMAKE_CACHE = CROSS_CMAKE_CACHE_COMMON | select({
    "//compile:gcc_build": {
        "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S",
        "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S",
        "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S",
    },
    "//compile:macos_build": {
        "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S",
        "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S",
        "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S",
    },
    "//conditions:default": {
        "LLVM_USE_LINKER": "lld",
        "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
        "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
        "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S -fuse-ld=lld",
    },
})

# aarch64 cross-compilation libraries.
cmake(
    name = "libcxx_cross_aarch64",
    cache_entries = CROSS_CMAKE_CACHE | {
        "CMAKE_C_COMPILER_TARGET": "aarch64-linux-gnu",
        "CMAKE_CXX_COMPILER_TARGET": "aarch64-linux-gnu",
        "CMAKE_ASM_COMPILER_TARGET": "aarch64-linux-gnu",
        "LLVM_DEFAULT_TARGET_TRIPLE": "aarch64-unknown-linux-gnu",
    },
    env = CROSS_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
        "libunwind.a",
    ],
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    working_directory = "runtimes",
)

pkg_files(
    name = "cross_aarch64_lib_files",
    srcs = [":libcxx_cross_aarch64"],
    excludes = [
        "**/*.h",
        "**/include/**",
    ],
    prefix = "cross-libs-aarch64/lib",
    strip_prefix = ".",
)

pkg_tar(
    name = "cxx_cross_aarch64",
    srcs = [":cross_aarch64_lib_files"],
    extension = "tar.xz",
    package_file_name = "cross-llvm%s-aarch64.tar.xz" % VERSIONS["llvm"],
)

# x86_64 cross-compilation libraries.
cmake(
    name = "libcxx_cross_x86_64",
    cache_entries = CROSS_CMAKE_CACHE | {
        "CMAKE_C_COMPILER_TARGET": "x86_64-linux-gnu",
        "CMAKE_CXX_COMPILER_TARGET": "x86_64-linux-gnu",
        "CMAKE_ASM_COMPILER_TARGET": "x86_64-linux-gnu",
        "LLVM_DEFAULT_TARGET_TRIPLE": "x86_64-unknown-linux-gnu",
    },
    env = CROSS_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
        "libunwind.a",
    ],
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    working_directory = "runtimes",
)

pkg_files(
    name = "cross_x86_64_lib_files",
    srcs = [":libcxx_cross_x86_64"],
    excludes = [
        "**/*.h",
        "**/include/**",
    ],
    prefix = "cross-libs-x86_64/lib",
    strip_prefix = ".",
)

pkg_tar(
    name = "cxx_cross_x86_64",
    srcs = [":cross_x86_64_lib_files"],
    extension = "tar.xz",
    package_file_name = "cross-llvm%s-x86_64.tar.xz" % VERSIONS["llvm"],
)
