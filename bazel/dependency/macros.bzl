
def updater(
        name,
        dependencies,
        version_file,
        jq_toolchain = "@jq_toolchains//:resolved_toolchain",
        update_script = "@envoy_toolshed//dependency:bazel-update.sh",
        sha_updater = "@envoy_toolshed//sha:replace",
        data = None,
        deps = None,
        toolchains = None,
):
    toolchains = [jq_toolchain] + (toolchains or [])
    data = (data or []) + [
        jq_toolchain,
        sha_updater,
        update_script,
        dependencies,
        version_file,
    ]
    args = [
        "$(JQ_BIN)",
        "$(location %s)" % sha_updater,
        "$(location %s)" % version_file,
        "$(location %s)" % dependencies,
    ]
    native.sh_binary(
        name = name,
        srcs = [update_script],
        data = data,
        args = args,
        deps = deps or [],
        toolchains = toolchains,
    )
