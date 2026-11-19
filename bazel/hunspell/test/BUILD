load("@rules_shell//shell:sh_test.bzl", "sh_test")
load(":hunspell_test.bzl", "hunspell_toolchain_test", "render_hub_build_test")

exports_files([
    "assert_hunspell_pipe.sh",
])

# Resolves `//hunspell:toolchain_type` (the prebuilt on Linux, the source fallback eg on macOS)
# and checks the ispell pipe protocol with an empty environment.
hunspell_toolchain_test(
    name = "hunspell_toolchain_test",
    check = "assert_hunspell_pipe.sh",
    target_compatible_with = select({
        "@platforms//os:linux": [],
        "@platforms//os:macos": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
)

render_hub_build_test(
    name = "render_hub_build_test",
)

# The source build that the fallback toolchain uses, run directly: toolchain resolution prefers
# the prebuilt where there is one. Unconstrained, so CI also builds it for macOS.
sh_test(
    name = "hunspell_source_test",
    size = "small",
    srcs = [":assert_hunspell_pipe.sh"],
    args = [
        "$(rootpath @hunspell_src//:hunspell)",
        "$(rootpath @dictionary_en//:index.dic)",
    ],
    data = [
        "@dictionary_en//:index.aff",
        "@dictionary_en//:index.dic",
        "@hunspell_src//:hunspell",
    ],
)
