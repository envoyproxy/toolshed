load("//git:defs.bzl", "git_toolchain")
load("//git/private:git_package.bzl", "git_package")
load("//git/private:git_source.bzl", "git_source_wrapper")

git_source_wrapper(
    name = "source_git",
    cacert = "@cacert//file",
    git = "@git//:git",
    git_remote_http = "@git//:git-remote-http",
    templates = "@git//:templates",
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
)

git_toolchain(
    name = "source_impl",
    git = ":source_git",
)

toolchain(
    name = "source_toolchain",
    toolchain = ":source_impl",
    toolchain_type = "//git:toolchain_type",
    visibility = ["//visibility:public"],
)

git_package(
    name = "git_linux_x86_64",
    platform = "linux-x86_64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
    visibility = ["//visibility:public"],
)

git_package(
    name = "git_linux_aarch64",
    platform = "linux-aarch64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
    visibility = ["//visibility:public"],
)

filegroup(
    name = "git_packages",
    srcs = [
        ":git_linux_aarch64",
        ":git_linux_x86_64",
    ],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
