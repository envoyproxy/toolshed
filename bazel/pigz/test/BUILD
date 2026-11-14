load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//:versions.bzl", "VERSIONS")
load(":pigz_test.bzl", "render_hub_build_test", "unavailable_test")

exports_files([
    "assert_pigz_roundtrip.sh",
])

# `//pigz`, resolved through `//pigz:toolchain_type` (the prebuilt, on Linux), as consumers use it.
sh_test(
    name = "pigz_toolchain_test",
    size = "small",
    srcs = [":assert_pigz_roundtrip.sh"],
    args = ["$(rootpath //pigz)"],
    data = ["//pigz"],
    # Without prebuilts (until the release preparation sets their hashes) there is no pigz.
    tags = [] if all(VERSIONS["pigz_sha256"].values()) else ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
)

render_hub_build_test(
    name = "render_hub_build_test",
)

# A platform that the prebuilt toolchains do not match.
platform(
    name = "no_pigz_platform",
    constraint_values = [
        "@platforms//cpu:x86_64",
        "@platforms//os:windows",
    ],
)

# Without a pigz for the platform, `//pigz` fails with a message, rather than building pigz.
unavailable_test(
    name = "unavailable_test",
    target_under_test = "//pigz",
)
