"""Build and package the registry git source target for Linux toolchains."""

load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
load("//:versions.bzl", "VERSIONS")

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

def _copy_file(ctx, src, out, progress_message):
    ctx.actions.run_shell(
        inputs = [src],
        outputs = [out],
        command = "mkdir -p $(dirname \"$2\") && cp -f \"$1\" \"$2\"",
        arguments = [src.path, out.path],
        mnemonic = "GitCopyFile",
        progress_message = progress_message,
    )

_BUILD_BAZEL = """exports_files(glob(["**"]))
filegroup(name = "git", srcs = ["bin/git"], visibility = ["//visibility:public"])
filegroup(name = "runtime", srcs = glob(["libexec/**", "share/**"]), visibility = ["//visibility:public"])
"""

def _template_dest(src):
    parts = src.short_path.split("/templates/", 1)
    if len(parts) != 2:
        fail("template path missing /templates/: %s" % src.short_path)
    return "share/git-core/templates/" + parts[1]

def _want_template(rel):
    return (
        rel == "share/git-core/templates/description" or
        rel == "share/git-core/templates/info/exclude" or
        (
            rel.startswith("share/git-core/templates/hooks/") and
            rel.endswith(".sample")
        )
    )

def _git_files_impl(ctx):
    package_dir = "git-%s-%s" % (VERSIONS["git"], ctx.attr.platform)
    git = ctx.attr.git[0][DefaultInfo].files.to_list()[0]
    git_remote_http = ctx.attr.git_remote_http[0][DefaultInfo].files.to_list()[0]
    templates = sorted(ctx.attr.templates[0][DefaultInfo].files.to_list(), key = lambda f: f.short_path)

    git_wrapper = ctx.actions.declare_file(package_dir + "/bin/git")
    git_out = ctx.actions.declare_file(package_dir + "/libexec/git-core/git")
    git_remote_http_out = ctx.actions.declare_file(package_dir + "/libexec/git-core/git-remote-http")
    executables = [git_wrapper, git_out, git_remote_http_out]
    data = []

    _strip_binary(ctx, git, git_out, "Stripping git for " + ctx.attr.platform)
    _strip_binary(ctx, git_remote_http, git_remote_http_out, "Stripping git-remote-http for " + ctx.attr.platform)
    for src in templates:
        rel = _template_dest(src)
        if not _want_template(rel):
            continue
        out = ctx.actions.declare_file(package_dir + "/" + rel)
        _copy_file(ctx, src, out, "Copying template %s for %s" % (rel, ctx.attr.platform))
        if rel.startswith("share/git-core/templates/hooks/"):
            executables.append(out)
        else:
            data.append(out)
    ctx.actions.write(
        output = git_wrapper,
        content = """#!/bin/sh
self=$0
case "$self" in
    /*) ;;
    *) self="$(pwd)/$self" ;;
esac
while [ -L "$self" ]; do
    link="$(readlink "$self")"
    case "$link" in
        /*) self="$link" ;;
        *) self="$(dirname "$self")/$link" ;;
    esac
done
here="$(CDPATH= cd "$(dirname "$self")/.." && pwd)"
export GIT_EXEC_PATH="$here/libexec/git-core"
export GIT_TEMPLATE_DIR="$here/share/git-core/templates"
: "${GIT_SSL_CAINFO:=${TOOLSHED_CA_BUNDLE:-$here/share/git-core/ca-certificates.crt}}"
export GIT_SSL_CAINFO
export SSL_CERT_FILE="$GIT_SSL_CAINFO"
exec "$GIT_EXEC_PATH/git" "$@"
""",
        is_executable = True,
    )

    return [
        DefaultInfo(files = depset(executables + data)),
        OutputGroupInfo(
            executables = depset(executables),
            data = depset(data),
        ),
    ]

def git_files_rule(git_platform_transition, platforms):
    return rule(
        implementation = _git_files_impl,
        attrs = {
            "git": attr.label(
                mandatory = True,
                executable = True,
                cfg = git_platform_transition,
            ),
            "git_remote_http": attr.label(
                mandatory = True,
                executable = True,
                cfg = git_platform_transition,
            ),
            "templates": attr.label(
                mandatory = True,
                cfg = git_platform_transition,
            ),
            "platform": attr.string(mandatory = True, values = sorted(platforms.keys())),
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

def git_package(name, platform, stripper, git_files, git, git_remote_http, templates, cacert, visibility = None):
    """Build the published git tarball for one platform.

    Args:
        name: Macro target name.
        platform: Artifact platform suffix.
        stripper: Executable used to strip git binaries.
        visibility: Optional visibility for the final tarball target.
    """
    package_dir = "git-%s-%s" % (VERSIONS["git"], platform)
    files = name + "_files"
    executables = name + "_executables"
    data = name + "_data"
    build = name + "_build"
    packaging_build = name + "_build_files"
    packaging_exec = name + "_packaging_exec"
    packaging_data = name + "_packaging_data"
    packaging_cacert = name + "_packaging_cacert"
    https_link = name + "_https_link"
    package_tar = name + "_pkg_tar"
    tarball = name + "_tar"

    native.genrule(
        name = build,
        outs = [package_dir + "/BUILD.bazel"],
        cmd = """cat >"$@" <<'EOF'
%sEOF""" % _BUILD_BAZEL,
        tags = ["manual"],
    )
    git_files(
        name = files,
        git = git,
        git_remote_http = git_remote_http,
        platform = platform,
        stripper = stripper,
        tags = ["manual"],
        templates = templates,
    )
    native.filegroup(
        name = executables,
        srcs = [":" + files],
        output_group = "executables",
        tags = ["manual"],
    )
    native.filegroup(
        name = data,
        srcs = [":" + files],
        output_group = "data",
        tags = ["manual"],
    )
    pkg_files(
        name = packaging_build,
        srcs = [":" + build],
        attributes = pkg_attributes(mode = "0644"),
        strip_prefix = strip_prefix.from_pkg(package_dir),
        tags = ["manual"],
    )
    pkg_files(
        name = packaging_exec,
        srcs = [":" + executables],
        attributes = pkg_attributes(mode = "0755"),
        strip_prefix = strip_prefix.from_pkg(package_dir),
        tags = ["manual"],
    )
    pkg_files(
        name = packaging_data,
        srcs = [":" + data],
        attributes = pkg_attributes(mode = "0644"),
        strip_prefix = strip_prefix.from_pkg(package_dir),
        tags = ["manual"],
    )
    pkg_files(
        name = packaging_cacert,
        srcs = [cacert],
        attributes = pkg_attributes(mode = "0644"),
        prefix = "share/git-core",
        renames = {cacert: "ca-certificates.crt"},
        tags = ["manual"],
    )
    pkg_mklink(
        name = https_link,
        link_name = "libexec/git-core/git-remote-https",
        target = "git-remote-http",
        tags = ["manual"],
    )
    pkg_tar(
        name = package_tar,
        extension = "tar",
        owner = "0.0",
        package_dir = package_dir,
        package_file_name = package_dir + ".tar",
        srcs = [
            ":" + packaging_build,
            ":" + packaging_exec,
            ":" + packaging_data,
            ":" + packaging_cacert,
            ":" + https_link,
        ],
        tags = ["manual"],
    )
    native.genrule(
        name = tarball,
        srcs = [":" + package_tar],
        outs = [package_dir + ".tar.zst"],
        cmd = "$(location @@aspect_bazel_lib++toolchains+zstd_linux_amd64//:zstd) -19 -T4 -f $(location :%s) -o $@" % package_tar,
        exec_properties = {"Pool": "linux_x64_xlarge"},
        tools = ["@@aspect_bazel_lib++toolchains+zstd_linux_amd64//:zstd"],
        tags = ["manual"],
    )
    native.filegroup(
        name = name,
        srcs = [":" + tarball],
        tags = ["manual"],
        visibility = visibility,
    )
