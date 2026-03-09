load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
load("//:versions.bzl", "VERSIONS")

package(default_visibility = ["//visibility:public"])

exports_files(["libcxx_cross.bzl", "extensions.bzl"])

# aarch64 cross-compilation libraries.
# Extracted from the official LLVM prebuilt release tarball (@llvm_prebuilt_aarch64).
pkg_files(
    name = "cross_aarch64_lib_files",
    srcs = ["@llvm_prebuilt_aarch64//:cross_libs"],
    prefix = "cross-libs-aarch64",
    strip_prefix = ".",
)

pkg_files(
    name = "cross_aarch64_header_files",
    srcs = ["@llvm_prebuilt_aarch64//:config_site"],
    prefix = "cross-libs-aarch64",
    strip_prefix = ".",
)

pkg_tar(
    name = "cxx_cross_aarch64",
    srcs = [
        ":cross_aarch64_lib_files",
        ":cross_aarch64_header_files",
    ],
    extension = "tar.xz",
    package_file_name = "cross-llvm%s-aarch64.tar.xz" % VERSIONS["llvm"],
)

# x86_64 cross-compilation libraries.
# Extracted from the official LLVM prebuilt release tarball (@llvm_prebuilt_x86_64).
pkg_files(
    name = "cross_x86_64_lib_files",
    srcs = ["@llvm_prebuilt_x86_64//:cross_libs"],
    prefix = "cross-libs-x86_64",
    strip_prefix = ".",
)

pkg_files(
    name = "cross_x86_64_header_files",
    srcs = ["@llvm_prebuilt_x86_64//:config_site"],
    prefix = "cross-libs-x86_64",
    strip_prefix = ".",
)

pkg_tar(
    name = "cxx_cross_x86_64",
    srcs = [
        ":cross_x86_64_lib_files",
        ":cross_x86_64_header_files",
    ],
    extension = "tar.xz",
    package_file_name = "cross-llvm%s-x86_64.tar.xz" % VERSIONS["llvm"],
)
