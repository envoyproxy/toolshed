"""Source-built git wrapper matching the prebuilt runtime layout."""

load("//git/private:transitions.bzl", "openssl_transition")

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

def _copy_with_mode(ctx, src, out, mode):
    ctx.actions.run_shell(
        inputs = [src],
        outputs = [out],
        command = "mkdir -p $(dirname \"$3\") && cp -f \"$1\" \"$3\" && chmod \"$2\" \"$3\"",
        arguments = [src.path, mode, out.path],
        mnemonic = "GitSourceCopy",
        progress_message = "Preparing %s" % out.short_path,
    )

def _single_file(target, what):
    files = target[DefaultInfo].files.to_list()
    if len(files) != 1:
        fail("%s (%s) must provide exactly one file" % (what, target.label))
    return files[0]

def _git_source_wrapper_impl(ctx):
    git_target = ctx.attr.git[0]
    git = git_target[DefaultInfo].files_to_run.executable
    if not git:
        fail("`git` (%s) does not provide an executable" % git_target.label)
    git_remote_http_target = ctx.attr.git_remote_http[0]
    git_remote_http = git_remote_http_target[DefaultInfo].files_to_run.executable
    if not git_remote_http:
        fail("`git_remote_http` (%s) does not provide an executable" % git_remote_http_target.label)
    templates = sorted(ctx.attr.templates[0][DefaultInfo].files.to_list(), key = lambda f: f.short_path)
    cacert = _single_file(ctx.attr.cacert[0], "`cacert`")

    package_dir = ctx.label.name
    git_wrapper = ctx.actions.declare_file(package_dir + "/bin/git")
    git_out = ctx.actions.declare_file(package_dir + "/libexec/git-core/git")
    git_remote_http_out = ctx.actions.declare_file(package_dir + "/libexec/git-core/git-remote-http")
    git_remote_https_out = ctx.actions.declare_file(package_dir + "/libexec/git-core/git-remote-https")
    cacert_out = ctx.actions.declare_file(package_dir + "/share/git-core/ca-certificates.crt")

    outputs = [git_wrapper, git_out, git_remote_http_out, git_remote_https_out, cacert_out]

    ctx.actions.symlink(output = git_out, target_file = git, is_executable = True)
    ctx.actions.symlink(output = git_remote_http_out, target_file = git_remote_http, is_executable = True)

    # Point declared symlinks directly at real input Files so remote execution
    # never has to materialize a symlink-to-symlink chain for git-remote-https.
    ctx.actions.symlink(output = git_remote_https_out, target_file = git_remote_http, is_executable = True)
    ctx.actions.symlink(output = cacert_out, target_file = cacert)

    for src in templates:
        rel = _template_dest(src)
        if not _want_template(rel):
            continue
        out = ctx.actions.declare_file(package_dir + "/" + rel)
        _copy_with_mode(
            ctx,
            src,
            out,
            "755" if rel.startswith("share/git-core/templates/hooks/") else "644",
        )
        outputs.append(out)

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

    return [DefaultInfo(
        executable = git_wrapper,
        files = depset(outputs),
        runfiles = ctx.runfiles(files = outputs),
    )]

git_source_wrapper = rule(
    implementation = _git_source_wrapper_impl,
    executable = True,
    attrs = {
        "cacert": attr.label(
            mandatory = True,
            cfg = openssl_transition,
        ),
        "git": attr.label(
            mandatory = True,
            executable = True,
            cfg = openssl_transition,
        ),
        "git_remote_http": attr.label(
            mandatory = True,
            executable = True,
            cfg = openssl_transition,
        ),
        "templates": attr.label(
            mandatory = True,
            cfg = openssl_transition,
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
)
