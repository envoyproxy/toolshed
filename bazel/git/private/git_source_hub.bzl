"""Repository rule for consumer-configured git source toolchains and packages."""

_TRANSITIONS_TEMPLATE = """\
GIT_PLATFORMS = {{
    "linux-x86_64": "@@toolchains_llvm+//platforms:linux-x86_64",
    "linux-aarch64": "@@toolchains_llvm+//platforms:linux-aarch64",
}}

def _git_platform_transition_impl(_settings, attr):
    return {{
        "//command_line_option:platforms": [GIT_PLATFORMS[attr.platform]],
        "{ssl_lib_label}": "openssl",
    }}

git_platform_transition = transition(
    implementation = _git_platform_transition_impl,
    inputs = [],
    outputs = [
        "//command_line_option:platforms",
        "{ssl_lib_label}",
    ],
)

def _openssl_transition_impl(_settings, _attr):
    return {{
        "{ssl_lib_label}": "openssl",
    }}

openssl_transition = transition(
    implementation = _openssl_transition_impl,
    inputs = [],
    outputs = ["{ssl_lib_label}"],
)
"""

_DEFS_TEMPLATE = """\
load("{git_package_bzl_label}", "git_files_rule")
load("{git_source_bzl_label}", "git_source_wrapper_rule")
load(":transitions.bzl", "GIT_PLATFORMS", "git_platform_transition", "openssl_transition")

git_files = git_files_rule(
    git_platform_transition = git_platform_transition,
    platforms = GIT_PLATFORMS,
)

git_source_wrapper = git_source_wrapper_rule(openssl_transition)
"""

_BUILD_TEMPLATE = """\
load(":defs.bzl", "git_files", "git_source_wrapper")
load("{git_package_bzl_label}", "git_package")
load("{toolchain_bzl_label}", "git_toolchain")

git_source_wrapper(
    name = "source_git",
    cacert = "{cacert_label}",
    git = "{git_label}",
    git_remote_http = "{git_remote_http_label}",
    target_compatible_with = select({{
        "{gcc_build_label}": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }}),
    templates = "{templates_label}",
)

git_toolchain(
    name = "source_impl",
    git = ":source_git",
)

toolchain(
    name = "source_toolchain",
    toolchain = ":source_impl",
    toolchain_type = "{toolchain_type_label}",
    visibility = ["//visibility:public"],
)

git_package(
    name = "git_linux_x86_64",
    cacert = "{cacert_label}",
    git = "{git_label}",
    git_files = git_files,
    git_remote_http = "{git_remote_http_label}",
    platform = "linux-x86_64",
    stripper = "{stripper_label}",
    templates = "{templates_label}",
    visibility = ["//visibility:public"],
)

git_package(
    name = "git_linux_aarch64",
    cacert = "{cacert_label}",
    git = "{git_label}",
    git_files = git_files,
    git_remote_http = "{git_remote_http_label}",
    platform = "linux-aarch64",
    stripper = "{stripper_label}",
    templates = "{templates_label}",
    visibility = ["//visibility:public"],
)

filegroup(
    name = "git_packages",
    srcs = [
        ":git_linux_aarch64",
        ":git_linux_x86_64",
    ],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
"""

def render_git_source_transitions(ssl_lib_label):
    return _TRANSITIONS_TEMPLATE.format(ssl_lib_label = ssl_lib_label)

def render_git_source_build(
        *,
        cacert_label,
        gcc_build_label,
        git_label,
        git_package_bzl_label,
        git_remote_http_label,
        stripper_label,
        templates_label,
        toolchain_bzl_label,
        toolchain_type_label):
    return _BUILD_TEMPLATE.format(
        cacert_label = cacert_label,
        gcc_build_label = gcc_build_label,
        git_label = git_label,
        git_package_bzl_label = git_package_bzl_label,
        git_remote_http_label = git_remote_http_label,
        stripper_label = stripper_label,
        templates_label = templates_label,
        toolchain_bzl_label = toolchain_bzl_label,
        toolchain_type_label = toolchain_type_label,
    )

def render_git_source_defs(
        *,
        git_package_bzl_label,
        git_source_bzl_label):
    return _DEFS_TEMPLATE.format(
        git_package_bzl_label = git_package_bzl_label,
        git_source_bzl_label = git_source_bzl_label,
    )

def _git_source_hub_impl(ctx):
    ctx.file("defs.bzl", render_git_source_defs(
        git_package_bzl_label = ctx.attr.git_package_bzl_label,
        git_source_bzl_label = ctx.attr.git_source_bzl_label,
    ))
    ctx.file("transitions.bzl", render_git_source_transitions(str(ctx.attr.ssl_lib)))
    ctx.file("BUILD.bazel", render_git_source_build(
        cacert_label = str(ctx.attr.cacert),
        gcc_build_label = ctx.attr.gcc_build_label,
        git_label = str(ctx.attr.git),
        git_package_bzl_label = ctx.attr.git_package_bzl_label,
        git_remote_http_label = str(ctx.attr.git_remote_http),
        stripper_label = str(ctx.attr.stripper),
        templates_label = str(ctx.attr.templates),
        toolchain_bzl_label = ctx.attr.toolchain_bzl_label,
        toolchain_type_label = ctx.attr.toolchain_type_label,
    ))
    return ctx.repo_metadata(reproducible = True)

git_source_hub = repository_rule(
    implementation = _git_source_hub_impl,
    attrs = {
        "cacert": attr.label(mandatory = True),
        "gcc_build_label": attr.string(mandatory = True),
        "git": attr.label(mandatory = True),
        "git_package_bzl_label": attr.string(mandatory = True),
        "git_remote_http": attr.label(mandatory = True),
        "git_source_bzl_label": attr.string(mandatory = True),
        "ssl_lib": attr.label(mandatory = True),
        "stripper": attr.label(mandatory = True),
        "templates": attr.label(mandatory = True),
        "toolchain_bzl_label": attr.string(mandatory = True),
        "toolchain_type_label": attr.string(mandatory = True),
    },
)
