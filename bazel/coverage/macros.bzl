"""Portable coverage reporting and threshold validation."""

load("@aspect_bazel_lib//lib:jq.bzl", "jq")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("//coverage/lcov:lcov_merge_repository.bzl", "LCOV_MERGE_PLATFORMS")

_JQ = Label("@jq_toolchains//:resolved_toolchain")

# jq with the toolshed modules importable, for the report filter.
_TOOLSHED_JQ = Label("@envoy_toolshed_jq//:jq")
_MAIN = Label("@envoy_toolshed_jq//:coverage/main.jq")
_GENERATOR = Label("//coverage:report_generator.sh")
_VALIDATOR = Label("//coverage:validate.sh")
_RUNFILES = Label("@bazel_tools//tools/bash/runfiles")
_LCOV_MERGE_SETTINGS = [Label("//coverage/lcov:" + platform) for platform in LCOV_MERGE_PLATFORMS]

def _on_lcov_merge_platforms(value, default):
    """`value` where the prebuilt lcov-merge exists, `default` elsewhere."""
    choices = {str(setting): value for setting in _LCOV_MERGE_SETTINGS}
    choices["//conditions:default"] = default
    return select(choices)
COVERAGE_ZSTD_TARGET = str(Label("@zstd//:zstd_cli"))
_TEMPLATES = {
    "base.html": Label("//coverage:templates/base.html"),
    "index.html": Label("//coverage:templates/index.html"),
    "macros.html": Label("//coverage:templates/macros.html"),
}

def _runfile_key(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return ctx.workspace_name + "/" + file.short_path

def _quote(value):
    return "'" + value.replace("'", "'\"'\"'") + "'"

def _tool_file(target):
    """The file a tool attribute refers to: its executable, or its single file."""
    if not target:
        return None
    info = target[DefaultInfo]
    if info.files_to_run and info.files_to_run.executable:
        return info.files_to_run.executable
    files = info.files.to_list()
    if len(files) != 1:
        fail("%s must be an executable or a single file" % target.label)
    return files[0]

def _configured_script_impl(ctx):
    exports = []
    for name in [
        "COVERAGE_CONFIG",
        "GRCOV",
        "GRCOV_CONFIG",
        "JQ_BIN",
        "JQ_FILTER",
        "LCOV_MERGE",
        "TEMPLATE_BASE",
        "TEMPLATE_INDEX",
        "TEMPLATE_MACROS",
        "ZSTD_BIN",
    ]:
        file = _tool_file(getattr(ctx.attr, name.lower()))
        if file:
            exports.append("export %s=%s" % (name, _quote(_runfile_key(ctx, file))))
    exports.extend([
        "export SOURCE_ROOT=%s" % _quote(ctx.attr.source_root),
        "export SOURCE_GLOB=%s" % _quote(ctx.attr.source_glob),
    ])
    output = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.expand_template(
        template = ctx.file.script,
        output = output,
        substitutions = {"#!/usr/bin/env bash": "#!/usr/bin/env bash\n" + "\n".join(exports)},
        is_executable = True,
    )
    return [DefaultInfo(files = depset([output]))]

_configured_script = rule(
    implementation = _configured_script_impl,
    attrs = dict(
        {
            # Tools may be executable targets (their executable is used) or single files.
            name: attr.label(allow_files = True)
            for name in [
                "coverage_config",
                "grcov",
                "grcov_config",
                "jq_bin",
                "jq_filter",
                "lcov_merge",
                "template_base",
                "template_index",
                "template_macros",
                "zstd_bin",
            ]
        },
        script = attr.label(allow_single_file = True),
        source_root = attr.string(),
        source_glob = attr.string(),
    ),
)

def coverage_report(
        name,
        config,
        templates = None,
        source_root = "source",
        source_glob = "*.cc",
        zstd = Label("@zstd//:zstd_cli"),
        grcov = "@grcov//:grcov",
        lcov_merge = None,
        visibility = None):
    """Create a report generator and a `<name>.validate` threshold checker.

    Args:
        name: Report generator target name.
        config: JSON coverage configuration label (may be generated).
        templates: Optional three labels in base, index, macros order, or a
            dictionary overriding those filenames.
        source_root: Workspace-relative source directory used for discovery.
        source_glob: Source filename pattern used for discovery.
        zstd: Archive compressor executable.
        grcov: Consumer-configured grcov executable label.
        lcov_merge: Optional `lcov-merge` executable label (see //coverage/lcov). When set,
            the per-test tracefiles are merged into one with it before grcov runs, and the
            baseline report is written as that merged tracefile without rendering. Only
            used on the platforms the prebuilt exists for; elsewhere grcov merges as before.
        visibility: Visibility of generated executable targets.
    """

    # Keep grcov caller-relative: toolshed's own repository mapping is dev-only.
    resolved_templates = dict(_TEMPLATES)
    overrides = templates or {}
    if type(overrides) == "list" or type(overrides) == "tuple":
        if len(overrides) != 3:
            fail("Coverage templates must contain base, index and macros labels")
        overrides = dict(zip(["base.html", "index.html", "macros.html"], overrides))
    for key, value in overrides.items():
        if key not in _TEMPLATES:
            fail("Unknown coverage template: %s" % key)
        resolved_templates[key] = value

    jq(
        name = name + "_grcov_config",
        srcs = [],
        out = name + "_grcov_config.json",
        filter = '{templates: {"base.html": $base, "index.html": $index, "macros.html": $macros}}',
        args = [
            "-n",
            "--arg",
            "base",
            "$(rootpath %s)" % resolved_templates["base.html"],
            "--arg",
            "index",
            "$(rootpath %s)" % resolved_templates["index.html"],
            "--arg",
            "macros",
            "$(rootpath %s)" % resolved_templates["macros.html"],
        ],
        data = resolved_templates.values(),
        expand_args = True,
    )

    grcov_config = ":" + name + "_grcov_config"

    # sh_binary.env is applied by `bazel run`, but not by coverage actions or
    # other binaries executing this tool. Embed the runfile keys as well.
    _configured_script(
        name = name + "_script",
        script = _GENERATOR,
        coverage_config = config,
        grcov = grcov,
        grcov_config = grcov_config,
        jq_bin = _TOOLSHED_JQ,
        jq_filter = _MAIN,
        lcov_merge = _on_lcov_merge_platforms(lcov_merge, None) if lcov_merge else None,
        template_base = resolved_templates["base.html"],
        template_index = resolved_templates["index.html"],
        template_macros = resolved_templates["macros.html"],
        zstd_bin = zstd,
        source_root = source_root,
        source_glob = source_glob,
    )
    env = {
        "COVERAGE_CONFIG": "$(rlocationpath %s)" % config,
        "GRCOV": "$(rlocationpath %s)" % grcov,
        "GRCOV_CONFIG": "$(rlocationpath %s)" % grcov_config,
        "JQ_BIN": "$(rlocationpath %s)" % _TOOLSHED_JQ,
        "JQ_FILTER": "$(rlocationpath %s)" % _MAIN,
        "SOURCE_GLOB": source_glob,
        "SOURCE_ROOT": source_root,
        "TEMPLATE_BASE": "$(rlocationpath %s)" % resolved_templates["base.html"],
        "TEMPLATE_INDEX": "$(rlocationpath %s)" % resolved_templates["index.html"],
        "TEMPLATE_MACROS": "$(rlocationpath %s)" % resolved_templates["macros.html"],
        "ZSTD_BIN": "$(rlocationpath %s)" % zstd,
    }
    data = [
        config,
        grcov,
        grcov_config,
        zstd,
        _TOOLSHED_JQ,
        _MAIN,
    ] + resolved_templates.values()
    if lcov_merge:
        # The prebuilt only exists for some platforms; elsewhere the merger is left out and
        # the generator merges with grcov as before.
        env = env | _on_lcov_merge_platforms({"LCOV_MERGE": "$(rlocationpath %s)" % lcov_merge}, {})
        data = data + _on_lcov_merge_platforms([lcov_merge], [])
    sh_binary(
        name = name,
        srcs = [":" + name + "_script"],
        data = data,
        deps = [_RUNFILES],
        env = env,
        visibility = visibility,
    )

    _configured_script(
        name = name + "_validate_script",
        script = _VALIDATOR,
        coverage_config = config,
        jq_bin = _JQ,
    )
    sh_binary(
        name = name + ".validate",
        srcs = [":" + name + "_validate_script"],
        data = [config, _JQ],
        deps = [_RUNFILES],
        env = {
            "COVERAGE_CONFIG": "$(rlocationpath %s)" % config,
            "JQ_BIN": "$(rlocationpath %s)" % _JQ,
        },
        visibility = visibility,
    )
