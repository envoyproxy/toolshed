"""Build and package the source-built hunspell and en_US dictionary for Linux toolchains.

Only loaded by toolshed's own `//hunspell/source` package (dev/bins release).
"""

load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "strip_prefix")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
load("//:versions.bzl", "VERSIONS")

HUNSPELL_PLATFORMS = {
    "linux-aarch64": "@@toolchains_llvm+//platforms:linux-aarch64",
    "linux-x86_64": "@@toolchains_llvm+//platforms:linux-x86_64",
}

_BUILD_BAZEL = """exports_files(glob(["**"]))
filegroup(name = "hunspell", srcs = ["bin/hunspell"], visibility = ["//visibility:public"])
filegroup(name = "dictionary", srcs = glob(["share/hunspell/*"]), visibility = ["//visibility:public"])
"""

def _platform_transition_impl(_settings, attr):
    return {"//command_line_option:platforms": [HUNSPELL_PLATFORMS[attr.platform]]}

_platform_transition = transition(
    implementation = _platform_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:platforms"],
)

def _run_shell(ctx, inputs, out, command, arguments, mnemonic, tools = []):
    ctx.actions.run_shell(
        inputs = inputs,
        tools = tools,
        outputs = [out],
        command = "mkdir -p $(dirname \"$1\") && " + command,
        arguments = [out.path] + arguments,
        mnemonic = mnemonic,
        progress_message = "Packaging %s" % out.short_path,
    )

def _hunspell_files_impl(ctx):
    package_dir = "hunspell-%s-%s" % (VERSIONS["hunspell"]["version"], ctx.attr.platform)
    hunspell = ctx.attr.hunspell[0][DefaultInfo].files_to_run.executable
    executables = []
    data = []

    out = ctx.actions.declare_file(package_dir + "/bin/hunspell")
    _run_shell(
        ctx,
        inputs = [hunspell],
        tools = [ctx.executable.stripper],
        out = out,
        command = "\"$2\" -o \"$1\" \"$3\"",
        arguments = [ctx.executable.stripper.path, hunspell.path],
        mnemonic = "HunspellStrip",
    )
    executables.append(out)

    copies = {
        "share/hunspell/en_US.aff": ctx.file.affix,
        "share/hunspell/en_US.dic": ctx.file.dictionary,
    }
    for target, path in ctx.attr.licenses.items():
        copies["share/doc/" + path] = target.files.to_list()[0]
    for dest, src in copies.items():
        out = ctx.actions.declare_file(package_dir + "/" + dest)
        _run_shell(
            ctx,
            inputs = [src],
            out = out,
            command = "cp -f \"$2\" \"$1\"",
            arguments = [src.path],
            mnemonic = "HunspellCopy",
        )
        data.append(out)

    return [
        DefaultInfo(files = depset(executables + data)),
        OutputGroupInfo(executables = depset(executables), data = depset(data)),
    ]

_hunspell_files = rule(
    implementation = _hunspell_files_impl,
    attrs = {
        "affix": attr.label(mandatory = True, allow_single_file = [".aff"]),
        "dictionary": attr.label(mandatory = True, allow_single_file = [".dic"]),
        "hunspell": attr.label(
            mandatory = True,
            executable = True,
            cfg = _platform_transition,
        ),
        "licenses": attr.label_keyed_string_dict(
            allow_files = True,
            doc = "License files, keyed to their path under `share/doc/`.",
        ),
        "platform": attr.string(mandatory = True, values = sorted(HUNSPELL_PLATFORMS.keys())),
        "stripper": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            allow_single_file = True,
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
)

def hunspell_package(name, platform, hunspell, affix, dictionary, licenses, stripper, visibility = None):
    """Build the published hunspell tarball for one platform.

    Args:
        name: Macro target name.
        platform: Artifact platform suffix.
        hunspell: Source-built `hunspell` executable.
        affix: Dictionary `.aff` file, packaged as `share/hunspell/en_US.aff`.
        dictionary: Dictionary `.dic` file, packaged as `share/hunspell/en_US.dic`.
        licenses: License files, keyed to their path under `share/doc/`.
        stripper: Executable used to strip the hunspell binary.
        visibility: Optional visibility for the final tarball target.
    """
    package_dir = "hunspell-%s-%s" % (VERSIONS["hunspell"]["version"], platform)
    files = name + "_files"
    tarball = name + "_tar"

    native.genrule(
        name = name + "_build",
        outs = [package_dir + "/BUILD.bazel"],
        cmd = """cat >"$@" <<'EOF'
%sEOF""" % _BUILD_BAZEL,
        tags = ["manual"],
    )
    _hunspell_files(
        name = files,
        affix = affix,
        dictionary = dictionary,
        hunspell = hunspell,
        licenses = licenses,
        platform = platform,
        stripper = stripper,
        tags = ["manual"],
    )
    for group, mode in [("executables", "0755"), ("data", "0644")]:
        native.filegroup(
            name = "%s_%s" % (name, group),
            srcs = [":" + files],
            output_group = group,
            tags = ["manual"],
        )
        pkg_files(
            name = "%s_pkg_%s" % (name, group),
            srcs = [":%s_%s" % (name, group)],
            attributes = pkg_attributes(mode = mode),
            strip_prefix = strip_prefix.from_pkg(package_dir),
            tags = ["manual"],
        )
    pkg_files(
        name = name + "_pkg_build",
        srcs = [":%s_build" % name],
        attributes = pkg_attributes(mode = "0644"),
        strip_prefix = strip_prefix.from_pkg(package_dir),
        tags = ["manual"],
    )
    pkg_tar(
        name = name + "_pkg_tar",
        extension = "tar",
        owner = "0.0",
        package_dir = package_dir,
        package_file_name = package_dir + ".tar",
        srcs = [
            ":%s_pkg_build" % name,
            ":%s_pkg_executables" % name,
            ":%s_pkg_data" % name,
        ],
        tags = ["manual"],
    )
    native.genrule(
        name = tarball,
        srcs = [":%s_pkg_tar" % name],
        outs = [package_dir + ".tar.zst"],
        cmd = "$(location @@aspect_bazel_lib++toolchains+zstd_linux_amd64//:zstd) -19 -T4 -f $(location :%s_pkg_tar) -o $@" % name,
        tools = ["@@aspect_bazel_lib++toolchains+zstd_linux_amd64//:zstd"],
        tags = ["manual"],
    )
    native.filegroup(
        name = name,
        srcs = [":" + tarball],
        tags = ["manual"],
        visibility = visibility,
    )
