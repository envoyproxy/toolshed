load("@rules_foreign_cc//foreign_cc:repositories.bzl", "rules_foreign_cc_dependencies")
load("@rules_python//python:repositories.bzl", "py_repositories")
load("@toolchains_llvm//toolchain:deps.bzl", "bazel_toolchain_dependencies")
load("@toolchains_llvm//toolchain:rules.bzl", "llvm_toolchain")
load("//:versions.bzl", "VERSIONS")

def resolve_dependencies(
        cmake_version=None,
        llvm_version=None,
        ninja_version=None):
    py_repositories()
    bazel_toolchain_dependencies()
    rules_foreign_cc_dependencies(
        register_preinstalled_tools = True,
        register_default_tools = True,
        cmake_version = cmake_version or VERSIONS["cmake"],
        ninja_version = ninja_version or VERSIONS["ninja"],
    )
    llvm_toolchain(
        name = "llvm_toolchain",
        llvm_version = llvm_version or VERSIONS["llvm"],
        sysroot = {
            "linux-x86_64": "@org_chromium_sysroot_linux_x64//:sysroot",
        },
    )
