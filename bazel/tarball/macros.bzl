
def unpacker(
        name,
        script = "@envoy_toolshed//tarball:unpack.sh",
        zstd = None,
        visibility = ["//visibility:public"],
):

    native.label_flag(
        name = "target",
        build_setting_default = ":target_default",
        visibility = ["//visibility:public"],
    )

    native.filegroup(
        name = "target_default",
        srcs = [],
    )

    env = {"TARGET": "$(location :target)"}
    data = [":target"]
    if zstd:
        data += [zstd]
        env["ZSTD"] = "$(location %s)" % zstd

    native.sh_binary(
        name = name,
        srcs = [script],
        visibility = visibility,
        data = data,
        env = env,
    )
