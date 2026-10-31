load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//:versions.bzl", "VERSIONS")
load(":hunspell_test.bzl", "hunspell_toolchain_test", "render_hub_build_test")

exports_files([
    "assert_hunspell_package.sh",
    "assert_hunspell_pipe.sh",
])

# Resolves `//hunspell:toolchain_type` (the source toolchain in toolshed, a prebuilt one
# once published) and checks the ispell pipe protocol with an empty environment.
hunspell_toolchain_test(
    name = "hunspell_toolchain_test",
    check = "assert_hunspell_pipe.sh",
    target_compatible_with = ["@platforms//os:linux"],
)

# The published tarballs, before publication: layout, modes, stripping and ELF checks for both
# arches, and the pipe check against the extracted package on a matching host.
[
    sh_test(
        name = "hunspell_linux_%s_package_test" % arch,
        size = "medium",
        srcs = [":assert_hunspell_package.sh"],
        data = [
            ":assert_hunspell_pipe.sh",
            "//compile:llvm_minimal_host_llvm_readelf",
            "//hunspell/source:hunspell_linux_%s" % arch,
            "@bsd_tar_toolchains//:resolved_toolchain",
        ],
        env = {
            "ARCH": arch,
            "GLIBC_FLOOR": "2.31",
            "HUNSPELL_VERSION": VERSIONS["hunspell"]["version"],
            "PIPE_CHECK": "$(rootpath :assert_hunspell_pipe.sh)",
            "READELF": "$(rootpath //compile:llvm_minimal_host_llvm_readelf)",
            "TAR": "$(rootpath @bsd_tar_toolchains//:resolved_toolchain)",
            "TARBALL": "$(rootpath //hunspell/source:hunspell_linux_%s)" % arch,
        },
        target_compatible_with = ["@platforms//os:linux"],
    )
    for arch in [
        "aarch64",
        "x86_64",
    ]
]

render_hub_build_test(
    name = "render_hub_build_test",
)
