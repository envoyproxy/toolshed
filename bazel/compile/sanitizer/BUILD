load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("//compile:llvm_runtimes.bzl", "BASE_CMAKE_CACHE", "PYTHON_CMAKE_CACHE", "SANITIZER_ENV")

package(default_visibility = ["//visibility:public"])

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
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
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
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    toolchains = ["@rules_python//python:current_py_toolchain"],
    working_directory = "runtimes",
)

filegroup(
    name = "libcxx_msan_headers",
    srcs = [":libcxx_msan"],
    output_group = "include",
)

pkg_files(
    name = "msan_libs_files",
    srcs = [":libcxx_msan"],
    excludes = [":libcxx_msan_headers"],
    prefix = "msan-libs-x86_64/lib",
    strip_prefix = ".",
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
)

filegroup(
    name = "libcxx_tsan_headers",
    srcs = [":libcxx_tsan"],
    output_group = "include",
)

pkg_files(
    name = "tsan_libs_files",
    srcs = [":libcxx_tsan"],
    excludes = [":libcxx_tsan_headers"],
    prefix = "tsan-libs-x86_64/lib",
    strip_prefix = ".",
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
)
