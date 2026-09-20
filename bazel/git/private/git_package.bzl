"""Build and package the registry git source target for Linux toolchains."""

load("@aspect_bazel_lib//lib:tar.bzl", "mtree_mutate", "mtree_spec", "tar")
load("@rules_pkg//pkg:providers.bzl", "PackageFilesInfo")
load("//:versions.bzl", "VERSIONS")

_PLATFORMS = {
    "Linux-X64": "@toolchains_llvm//platforms:linux-x86_64",
    "Linux-ARM64": "@toolchains_llvm//platforms:linux-aarch64",
}

def _git_transition_impl(settings, attr):
    return {"//command_line_option:platforms": [_PLATFORMS[attr.platform]]}

_git_transition = transition(
    implementation = _git_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:platforms"],
)

def _strip_binary(ctx, src, out, progress_message):
    ctx.actions.run_shell(
        inputs = [src],
        tools = [ctx.executable.stripper],
        outputs = [out],
        command = "mkdir -p $(dirname \"$3\") && \"$2\" -o \"$3\" \"$1\"",
        arguments = [src.path, ctx.executable.stripper.path, out.path],
        mnemonic = "GitStrip",
        progress_message = progress_message,
    )

def _template_dest(src):
    parts = src.short_path.split("/templates/", 1)
    if len(parts) != 2:
        fail("template path missing /templates/: %s" % src.short_path)
    return "share/git-core/templates/" + parts[1]

def _git_files_impl(ctx):
    package_dir = "git-%s-%s" % (VERSIONS["git"], ctx.attr.platform)
    git = ctx.attr.git[0][DefaultInfo].files.to_list()[0]
    git_remote_http = ctx.attr.git_remote_http[0][DefaultInfo].files.to_list()[0]
    git_remote_https = ctx.attr.git_remote_https[0][DefaultInfo].files.to_list()[0]
    templates = sorted(ctx.attr.templates[0][DefaultInfo].files.to_list(), key = lambda f: f.short_path)

    git_out = ctx.actions.declare_file(package_dir + "/bin/git")
    git_remote_http_out = ctx.actions.declare_file(package_dir + "/libexec/git-core/git-remote-http")
    git_remote_https_out = ctx.actions.declare_file(package_dir + "/libexec/git-core/git-remote-https")

    _strip_binary(ctx, git, git_out, "Stripping git for " + ctx.attr.platform)
    _strip_binary(ctx, git_remote_http, git_remote_http_out, "Stripping git-remote-http for " + ctx.attr.platform)
    _strip_binary(ctx, git_remote_https, git_remote_https_out, "Stripping git-remote-https for " + ctx.attr.platform)

    dest_src_map = {
        "bin/git": git_out,
        "libexec/git-core/git-remote-http": git_remote_http_out,
        "libexec/git-core/git-remote-https": git_remote_https_out,
    }
    for src in templates:
        dest_src_map[_template_dest(src)] = src

    return [
        DefaultInfo(files = depset([git_out, git_remote_http_out, git_remote_https_out] + templates)),
        PackageFilesInfo(dest_src_map = dest_src_map, attributes = {}),
    ]

git_files = rule(
    implementation = _git_files_impl,
    attrs = {
        "git": attr.label(
            mandatory = True,
            executable = True,
            cfg = _git_transition,
        ),
        "git_remote_http": attr.label(
            mandatory = True,
            executable = True,
            cfg = _git_transition,
        ),
        "git_remote_https": attr.label(
            mandatory = True,
            executable = True,
            cfg = _git_transition,
        ),
        "templates": attr.label(
            mandatory = True,
            cfg = _git_transition,
        ),
        "platform": attr.string(mandatory = True, values = _PLATFORMS.keys()),
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

def git_package(name, platform, stripper):
    package_dir = "git-%s-%s" % (VERSIONS["git"], platform)
    files = name + "_files"
    build = name + "_build"
    native.genrule(
        name = build,
        outs = [package_dir + "/BUILD.bazel"],
        cmd = """cat >"$@" <<'EOF'
exports_files([
    "bin/git",
    "libexec/git-core/git-remote-http",
    "libexec/git-core/git-remote-https",
])
filegroup(name = "git", srcs = ["bin/git"], visibility = ["//visibility:public"])
EOF""",
        tags = ["manual"],
    )
    git_files(
        name = files,
        git = "@git//:git",
        git_remote_http = "@git//:git-remote-http",
        git_remote_https = "@git//:git_remote_https",
        platform = platform,
        stripper = stripper,
        tags = ["manual"],
        templates = "@git//:templates",
    )
    mtree_spec(
        name = name + "_mtree_src",
        srcs = [":" + files, ":" + build],
        tags = ["manual"],
    )
    mtree_mutate(
        name = name + "_mtree",
        mtree = ":" + name + "_mtree_src",
        package_dir = package_dir,
        strip_prefix = "git/" + package_dir,
        tags = ["manual"],
    )
    tar(
        name = name,
        args = ["--options=zstd:compression-level=19,zstd:threads=4"],
        compress = "zstd",
        exec_properties = {"Pool": "linux_x64_xlarge"},
        mtree = ":" + name + "_mtree",
        out = package_dir + ".tar.zst",
        srcs = [":" + files, ":" + build],
        tags = ["manual"],
    )
