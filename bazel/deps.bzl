load("@rules_foreign_cc//foreign_cc:repositories.bzl", "rules_foreign_cc_dependencies")
load("@rules_perl//perl:deps.bzl", "perl_register_toolchains", "perl_rules_dependencies")
load("@rules_python//python:repositories.bzl", "py_repositories")
load("@toolchains_llvm//toolchain:deps.bzl", "bazel_toolchain_dependencies")
load("@toolchains_llvm//toolchain:rules.bzl", "llvm_toolchain")
load("//:versions.bzl", "VERSIONS")
load("//sysroot:sysroot.bzl", "setup_sysroots")
load("//autotools:setup.bzl", "setup_autotools")

def resolve_dependencies(
        cmake_version=None,
        llvm_version=None,
        ninja_version=None,
        setup_autotools_toolchain=True,
        autotools_local_tarball_path=None):
    py_repositories()
    bazel_toolchain_dependencies()
    rules_foreign_cc_dependencies(
        register_preinstalled_tools = True,
        register_default_tools = True,
        cmake_version = cmake_version or VERSIONS["cmake"],
        ninja_version = ninja_version or VERSIONS["ninja"],
    )
    perl_rules_dependencies()
    perl_register_toolchains()
    setup_sysroots()
    llvm_toolchain(
        name = "llvm_toolchain",
        llvm_version = llvm_version or VERSIONS["llvm"],
        sysroot = {
            "linux-x86_64": "@sysroot_linux_amd64//:sysroot",
            "linux-aarch64": "@sysroot_linux_arm64//:sysroot",
        }
    )
    if setup_autotools_toolchain:
        setup_autotools(local_tarball_path = autotools_local_tarball_path)
