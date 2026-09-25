#!/usr/bin/env bash
#
# Verifies that a downstream consumer can register only the prebuilt git and sq
# toolchains and still analyze targets that resolve
# `@envoy_toolshed//git:toolchain_type` and `@envoy_toolshed//pgp:toolchain_type`.

set -euo pipefail

workspace="${BUILD_WORKSPACE_DIRECTORY:?must be run with \`bazel run\`}"
cd "$workspace"

tmp="$(mktemp -d)"
output_root="$(mktemp -d)"
trap 'rm -rf "$tmp" "$output_root"' EXIT

cat > "$tmp/MODULE.bazel" <<EOF
module(
    name = "git_prebuilt_consumer",
    version = "1.0.0",
)

bazel_dep(name = "envoy_toolshed", version = "0.4.17-dev")

local_path_override(
    module_name = "envoy_toolshed",
    path = "${workspace}",
)

local_path_override(
    module_name = "envoy_toolshed_jq",
    path = "${workspace%/bazel}/jq",
)

git_prebuilt_ext = use_extension("@envoy_toolshed//git:extensions.bzl", "git_prebuilt_extension")
git_prebuilt_ext.setup()
use_repo(git_prebuilt_ext, "git_toolchains")

sq_prebuilt_ext = use_extension("@envoy_toolshed//pgp:extensions.bzl", "sq_prebuilt_extension")
sq_prebuilt_ext.setup()
use_repo(sq_prebuilt_ext, "sq_toolchains")

register_toolchains("@git_toolchains//:all")
register_toolchains("@sq_toolchains//:all")
EOF

cat > "$tmp/BUILD.bazel" <<'EOF'
genrule(
    name = "git_version",
    outs = ["git-version.txt"],
    cmd = "$(GIT) --version > $@",
    toolchains = ["@envoy_toolshed//git:toolchain_type"],
)

# pgp_toolchain exposes no make variables; requiring the toolchain type is
# enough to force resolution under --nobuild.
genrule(
    name = "sq_probe",
    outs = ["sq-probe.txt"],
    cmd = "echo ok > $@",
    toolchains = ["@envoy_toolshed//pgp:toolchain_type"],
)
EOF

(
    cd "$tmp"
    bazel \
        --output_user_root="$output_root" \
        build \
        --legacy_external_runfiles \
        --repo_env=BAZEL_DO_NOT_DETECT_CPP_TOOLCHAIN=1 \
        --repo_env=ANDROID_HOME= \
        --incompatible_default_to_explicit_init_py \
        --registry=https://bcr.bazel.build/ \
        --registry=https://raw.githubusercontent.com/envoyproxy/bazel-registry/060f772cd4675d6598b5a020d3f51ecdca64e584 \
        --repo_contents_cache= \
        --nobuild \
        //:git_version \
        //:sq_probe
)
