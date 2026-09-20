load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _archive_prefix(repo):
    prefix = repo.rstrip("/").split("/")[-1]
    if prefix.endswith(".git"):
        return prefix[:-4]
    return prefix

def _archive_url(ctx, hash_):
    return "{}{}.tar.gz".format(ctx.attr.url_prefix, hash_)

def _lines(text):
    return [line for line in text.split("\n") if line]

def _ls_remote_hash(ctx):
    result = ctx.execute(["git", "ls-remote", ctx.attr.repo, "refs/heads/{}".format(ctx.attr.branch)])
    if result.return_code:
        fail("Failed to resolve {} {}: {}".format(ctx.attr.repo, ctx.attr.branch, result.stderr))
    line = result.stdout.split("\n", 1)[0]
    if not line:
        fail("Failed to resolve {} {}".format(ctx.attr.repo, ctx.attr.branch))
    return line.split("\t", 1)[0]

def _check_data(ctx, hash_):
    skip_check = bool(ctx.getenv("REGISTRY_SKIP_CHECK"))
    if skip_check:
        return {
            "commit_exists": False,
            "is_ancestor": False,
            "skip_check": True,
            "tags": [],
        }

    result = ctx.execute([
        "git",
        "clone",
        "--quiet",
        "--bare",
        "--filter=blob:none",
        ctx.attr.repo,
        "registry.git",
    ])
    if result.return_code:
        fail("Failed to clone {}: {}".format(ctx.attr.repo, result.stderr))

    git = ["git", "-c", "safe.bareRepository=all", "-C", "registry.git"]

    exists = ctx.execute(git + ["cat-file", "-e", "{}^{{commit}}".format(hash_)])
    ancestor = ctx.execute(git + ["merge-base", "--is-ancestor", hash_, ctx.attr.branch])
    tags = ctx.execute(git + ["tag", "--points-at", hash_])
    if tags.return_code:
        fail("Failed to list tags for {}: {}".format(hash_, tags.stderr))

    return {
        "commit_exists": exists.return_code == 0,
        "is_ancestor": ancestor.return_code == 0,
        "skip_check": False,
        "tags": _lines(tags.stdout),
    }

def _module_index(ctx):
    modules_dir = ctx.path("modules")
    modules = {}
    if not modules_dir.exists:
        return {"modules": modules}

    for module_dir in sorted(modules_dir.readdir(), key = lambda entry: entry.basename):
        metadata = None
        metadata_path = module_dir.get_child("metadata.json")
        if metadata_path.exists:
            metadata = json.decode(ctx.read(metadata_path))

        versions = []
        for child in sorted(module_dir.readdir(), key = lambda entry: entry.basename):
            if child.basename != "metadata.json":
                versions.append(child.basename)

        modules[module_dir.basename] = {
            "versions": versions,
        }
        if metadata != None:
            modules[module_dir.basename]["metadata"] = metadata

    return {"modules": modules}

def _write_snapshot_repo(ctx, info_json, index_json):
    ctx.file("info.json", info_json + "\n")
    ctx.file("index.json", index_json + "\n")
    ctx.file("BUILD.bazel", """\
package(default_visibility = ["//visibility:public"])

exports_files(["info.json", "index.json"])

filegroup(
    name = "info",
    srcs = ["info.json"],
)

filegroup(
    name = "index",
    srcs = ["index.json"],
)
""")

def _registry_snapshot_impl(ctx):
    hash_ = ctx.getenv(ctx.attr.hash_env) or _ls_remote_hash(ctx)
    ctx.download_and_extract(
        _archive_url(ctx, hash_),
        stripPrefix = "{}-{}".format(_archive_prefix(ctx.attr.repo), hash_),
    )
    check = _check_data(ctx, hash_)
    info = dict(check)
    info["hash"] = hash_
    info["repo"] = ctx.attr.repo
    info["branch"] = ctx.attr.branch
    _write_snapshot_repo(
        ctx,
        json.encode(info),
        json.encode(_module_index(ctx)),
    )

def _registry_snapshot_local_impl(ctx):
    _write_snapshot_repo(ctx, ctx.attr.info_json, ctx.attr.index_json)

registry_snapshot = repository_rule(
    implementation = _registry_snapshot_impl,
    attrs = {
        "branch": attr.string(default = "main"),
        "hash_env": attr.string(default = "REGISTRY_HASH"),
        "repo": attr.string(mandatory = True),
        "url_prefix": attr.string(default = "https://github.com/envoyproxy/bazel-registry/archive/"),
    },
    environ = [
        "REGISTRY_HASH",
        "REGISTRY_SKIP_CHECK",
    ],
)

registry_snapshot_local = repository_rule(
    implementation = _registry_snapshot_local_impl,
    attrs = {
        "index_json": attr.string(mandatory = True),
        "info_json": attr.string(mandatory = True),
    },
)

_snapshot_tag = tag_class(attrs = {
    "branch": attr.string(default = "main"),
    "hash_env": attr.string(default = "REGISTRY_HASH"),
    "name": attr.string(mandatory = True),
    "repo": attr.string(mandatory = True),
    "url_prefix": attr.string(default = "https://github.com/envoyproxy/bazel-registry/archive/"),
})

def _registry_ext_impl(module_ctx):
    for mod in module_ctx.modules:
        for snapshot in mod.tags.snapshot:
            registry_snapshot(
                name = snapshot.name,
                repo = snapshot.repo,
                branch = snapshot.branch,
                hash_env = snapshot.hash_env,
                url_prefix = snapshot.url_prefix,
            )

registry_ext = module_extension(
    implementation = _registry_ext_impl,
    tag_classes = {"snapshot": _snapshot_tag},
)

def _flag_json_impl(ctx):
    out = ctx.actions.declare_file("{}.json".format(ctx.label.name))
    ctx.actions.write(out, json.encode(ctx.attr.flag[BuildSettingInfo].value) + "\n")
    return [DefaultInfo(files = depset([out]))]

flag_json = rule(
    implementation = _flag_json_impl,
    attrs = {
        "flag": attr.label(mandatory = True, providers = [BuildSettingInfo]),
    },
)

def _rlocationpath(ctx, file_):
    return "{}/{}".format(ctx.workspace_name, file_.short_path)

def _run_registry_update_impl(ctx):
    writer = ctx.executable.writer
    messages = ctx.file.messages
    report = ctx.file.report
    script = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.write(
        script,
        """#!/usr/bin/env bash
set -euo pipefail
f=bazel_tools/tools/bash/runfiles/runfiles.bash
source "${{RUNFILES_DIR:-$0.runfiles}}/$f" 2>/dev/null || source "$(grep -sm1 "^$f " "${{RUNFILES_MANIFEST_FILE:-/dev/null}}" | cut -d ' ' -f2-)" || exit 1
"$(rlocation "{writer}")"
messages="$(rlocation "{messages}")"
report="$(rlocation "{report}")"
if [[ -s "$messages" ]]; then
  cat "$messages"
fi
cat "$report"
""".format(
            writer = _rlocationpath(ctx, writer),
            messages = _rlocationpath(ctx, messages),
            report = _rlocationpath(ctx, report),
        ),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = [script, messages, report, ctx.file._runfiles]).merge(
        ctx.attr.writer[DefaultInfo].default_runfiles,
    )
    return [DefaultInfo(executable = script, files = depset([script]), runfiles = runfiles)]

run_registry_update = rule(
    implementation = _run_registry_update_impl,
    executable = True,
    attrs = {
        "messages": attr.label(mandatory = True, allow_single_file = True),
        "report": attr.label(mandatory = True, allow_single_file = True),
        "writer": attr.label(mandatory = True, executable = True, cfg = "target"),
        "_runfiles": attr.label(
            allow_single_file = True,
            default = "@bazel_tools//tools/bash/runfiles",
        ),
    },
)
