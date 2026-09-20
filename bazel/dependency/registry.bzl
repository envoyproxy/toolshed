"""Rules for resolving and rewriting Bazel registry pins."""

load("//git:defs.bzl", "GIT_TOOLCHAIN_TYPE")

REPO_REGISTRY_EXECUTION_REQUIREMENTS = {
    "local": "1",
    "no-cache": "1",
    "no-remote": "1",
    "requires-network": "1",
}

REPO_REGISTRY_MNEMONIC = "RepoRegistry"
REPO_REGISTRY_TOOLCHAINS = [GIT_TOOLCHAIN_TYPE]

def _repo_registry_impl(ctx):
    git_info = ctx.toolchains[GIT_TOOLCHAIN_TYPE].git
    out = ctx.actions.declare_file(ctx.label.name + ".txt")
    ctx.actions.run_shell(
        outputs = [out],
        tools = depset([git_info.git], transitive = [git_info.runfiles.files]),
        command = """
set -euo pipefail
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
export HOME="$tmpdir"
export GIT_CONFIG_NOSYSTEM=1
export GIT_TERMINAL_PROMPT=0
COMMIT=$("$5" ls-remote --exit-code "$1" "refs/heads/$2" | cut -f1)
if ! printf '%s\n' "$COMMIT" | grep -Eq '^[0-9a-f]{40}$'; then
    echo "expected 40-hex commit for $1 refs/heads/$2, got: '$COMMIT'" >&2
    exit 1
fi
echo "$3/$COMMIT" > "$4"
""",
        arguments = [ctx.attr.repo, ctx.attr.ref, ctx.attr.url, out.path, git_info.git.path],
        mnemonic = REPO_REGISTRY_MNEMONIC,
        progress_message = "Resolving %s@%s" % (ctx.attr.repo, ctx.attr.ref),
        execution_requirements = REPO_REGISTRY_EXECUTION_REQUIREMENTS,
    )
    return [DefaultInfo(files = depset([out]))]

repo_registry = rule(
    implementation = _repo_registry_impl,
    attrs = {
        "repo": attr.string(mandatory = True),
        "ref": attr.string(default = "main"),
        "url": attr.string(mandatory = True),
    },
    toolchains = REPO_REGISTRY_TOOLCHAINS,
)

def _registry_bazelrc_impl(ctx):
    out = ctx.actions.declare_file(ctx.label.name + "/" + ctx.file.bazelrc.basename)
    ctx.actions.run(
        inputs = [ctx.file.bazelrc, ctx.file.registry],
        outputs = [out],
        arguments = [ctx.file.bazelrc.path, ctx.file.registry.path, ctx.attr.url, out.path],
        executable = ctx.executable._registry_bazelrc,
        mnemonic = "RegistryBazelrc",
    )
    return [DefaultInfo(files = depset([out]))]

registry_bazelrc = rule(
    implementation = _registry_bazelrc_impl,
    attrs = {
        "_registry_bazelrc": attr.label(
            allow_single_file = True,
            cfg = "exec",
            default = Label("//dependency:registry_bazelrc.sh"),
            executable = True,
        ),
        "bazelrc": attr.label(mandatory = True, allow_single_file = True),
        "registry": attr.label(mandatory = True, allow_single_file = True),
        "url": attr.string(mandatory = True),
    },
)
