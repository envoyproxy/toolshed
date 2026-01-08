load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
load("//:versions.bzl", "VERSIONS")

package(default_visibility = ["//visibility:public"])

exports_files(["sanitizer_libs.bzl", "extensions.bzl"])

SANITIZER_ENV = {
    "CXXFLAGS": "-nostdinc++ -nostdlib++",
    "LDFLAGS": "-nostdlib++",
}

BASE_CMAKE_CACHE = {
    "CMAKE_BUILD_TYPE": "RelWithDebInfo",
    "CMAKE_INSTALL_PREFIX": ".",
    "CMAKE_POSITION_INDEPENDENT_CODE": "ON",
    "LLVM_ENABLE_RUNTIMES": "libcxxabi;libcxx;libunwind",
    "LLVM_USE_LINKER": "lld",
    "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
    "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
    "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S -fuse-ld=lld",
    "BUILD_SHARED_LIBS": "OFF",
    "LIBCXX_ENABLE_SHARED": "OFF",
    "LIBCXX_ENABLE_STATIC": "ON",
    "LIBCXXABI_ENABLE_SHARED": "OFF",
    "LIBCXXABI_ENABLE_STATIC": "ON",
    "LIBUNWIND_ENABLE_SHARED": "OFF",
    "LIBUNWIND_ENABLE_STATIC": "ON",
}

cmake(
    name = "libcxx_msan",
    cache_entries = BASE_CMAKE_CACHE | {
        "LLVM_USE_SANITIZER": "MemoryWithOrigins",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
    ],
    working_directory = "runtimes",
)

cmake(
    name = "libcxx_tsan",
    cache_entries = BASE_CMAKE_CACHE | {
        "LLVM_USE_SANITIZER": "Thread",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
    ],
    working_directory = "runtimes",
)

pkg_files(
    name = "msan_libs_files",
    srcs = [":libcxx_msan"],
    excludes = [
        "**/*.h",
        "**/include/**",
    ],
    prefix = "msan-libs-x86_64/lib",
    strip_prefix = ".",
)

pkg_tar(
    name = "cxx_msan",
    srcs = [":msan_libs_files"],
    extension = "tar.xz",
    package_file_name = "msan-llvm%s-x86_64.tar.xz" % VERSIONS["llvm"],
)

pkg_files(
    name = "tsan_libs_files",
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
)
