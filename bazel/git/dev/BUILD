load("//git:defs.bzl", "git_toolchain")
load("//git/private:git_source.bzl", "git_source_wrapper")

git_source_wrapper(
    name = "source_git",
    cacert = "@cacert//file",
    git = "@git//:git",
    git_remote_http = "@git//:git-remote-http",
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    templates = "@git//:templates",
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
