load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("//compile:llvm_runtimes.bzl", "BASE_CMAKE_CACHE", "PYTHON_CMAKE_CACHE", "SANITIZER_ENV")

package(default_visibility = ["//visibility:public"])

_LINUX_LLVM_ONLY = select({
    "//compile:gcc_build": ["@platforms//:incompatible"],
    "//compile:macos_build": ["@platforms//:incompatible"],
    "//conditions:default": [],
})

# Shared LLVM libunwind built against the toolshed sysroot.
#
# This exists only because the upstream LLVM release tarball's libunwind.so.1
# requires GLIBC_2.34 and the sysroot ships glibc 2.31. Once the sysroot
# baseline is >= 2.34 the tarball library can be used directly and this
# package (and @unwind_libs) can be removed.
cmake(
    name = "libunwind_shared",
    cache_entries = BASE_CMAKE_CACHE | PYTHON_CMAKE_CACHE | {
        "LLVM_ENABLE_RUNTIMES": "libunwind",
        "LIBUNWIND_ENABLE_SHARED": "ON",
        "LIBUNWIND_ENABLE_STATIC": "OFF",
        # The .so must not itself pull libgcc for builtins.
        "LIBUNWIND_USE_COMPILER_RT": "ON",
        "LIBUNWIND_INSTALL_LIBRARY_DIR": "lib",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_shared_libs = ["libunwind.so.1"],
    target_compatible_with = _LINUX_LLVM_ONLY,
    toolchains = ["@rules_python//python:current_py_toolchain"],
    working_directory = "runtimes",
)

filegroup(
    name = "libunwind_so_installed",
    srcs = [":libunwind_shared"],
    output_group = "libunwind.so.1",
)

# libunwind's install tree has libunwind.so.1.0 as the real file with
# libunwind.so.1 / libunwind.so as symlinks. Dereference so the packaged
# artifact (and cc_import consumers) always get a real libunwind.so.1 with
# SONAME libunwind.so.1, regardless of how the install dir was copied.
genrule(
    name = "libunwind_so",
    srcs = [":libunwind_so_installed"],
    outs = ["lib/libunwind.so.1"],
    cmd = "cp -L $(location :libunwind_so_installed) $@",
    target_compatible_with = _LINUX_LLVM_ONLY,
)

pkg_files(
    name = "unwind_libs_files",
    srcs = [":libunwind_so"],
    prefix = "unwind-libs-x86_64/lib",
    strip_prefix = "lib",
    target_compatible_with = _LINUX_LLVM_ONLY,
)
