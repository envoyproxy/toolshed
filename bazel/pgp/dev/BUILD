load("//pgp:defs.bzl", "pgp_toolchain", "sq_signer")
load("//pgp/private:sq_package.bzl", "sq_package")

sq_signer(
    name = "sq_signer",
    sq = "@sq//:sq_from_source",
    visibility = ["//visibility:public"],
)

pgp_toolchain(
    name = "sq_signer_toolchain",
    signer = ":sq_signer",
)

toolchain(
    name = "sq_toolchain",
    toolchain = ":sq_signer_toolchain",
    toolchain_type = "//pgp:toolchain_type",
    visibility = ["//visibility:public"],
)

sq_package(
    name = "sq_linux_x86_64",
    platform = "Linux-X64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
)

sq_package(
    name = "sq_linux_arm64",
    platform = "Linux-ARM64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
)

filegroup(
    name = "sq_packages",
    srcs = [":sq_linux_x86_64", ":sq_linux_arm64"],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
