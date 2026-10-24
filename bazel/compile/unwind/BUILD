load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("//compile:llvm_runtimes.bzl", "BASE_CMAKE_CACHE", "PYTHON_CMAKE_CACHE", "SANITIZER_ENV")

package(default_visibility = ["//visibility:public"])

cmake(
    name = "libunwind_shared",
    cache_entries = BASE_CMAKE_CACHE | PYTHON_CMAKE_CACHE | {
        "LLVM_ENABLE_RUNTIMES": "libunwind",
        "LIBUNWIND_ENABLE_SHARED": "ON",
        "LIBUNWIND_ENABLE_STATIC": "OFF",
        "LIBUNWIND_USE_COMPILER_RT": "ON",
        "LIBUNWIND_INSTALL_LIBRARY_DIR": "lib",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_shared_libs = ["libunwind.so.1"],
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    toolchains = ["@rules_python//python:current_py_toolchain"],
    working_directory = "runtimes",
)

filegroup(
    name = "libunwind_so",
    srcs = [":libunwind_shared"],
    output_group = "libunwind.so.1",
)

pkg_files(
    name = "unwind_libs_files",
    srcs = [":libunwind_so"],
    prefix = "unwind-libs-x86_64/lib",
    strip_prefix = ".",
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
)
