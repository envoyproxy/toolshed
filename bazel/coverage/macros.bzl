"""Portable coverage reporting and threshold validation."""

load("@aspect_bazel_lib//lib:jq.bzl", "jq")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

_JQ = Label("@jq_toolchains//:resolved_toolchain")
_MODULES = Label("@envoy_toolshed_jq//:modules")
_MARKER = Label("@envoy_toolshed_jq//:modules_root.marker")
_MAIN = Label("@envoy_toolshed_jq//:coverage/main.jq")
_GENERATOR = Label("//coverage:report_generator.sh")
_VALIDATOR = Label("//coverage:validate.sh")
_RUNFILES = Label("@bazel_tools//tools/bash/runfiles")
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

def _configured_script_impl(ctx):
    exports = []
    for name in [
        "COVERAGE_CONFIG",
        "GRCOV",
        "GRCOV_CONFIG",
        "JQ_BIN",
        "JQ_FILTER",
        "TEMPLATE_BASE",
        "TEMPLATE_INDEX",
        "TEMPLATE_MACROS",
        "TOOLSHED_JQ_ROOT",
        "ZSTD_BIN",
    ]:
        file = getattr(ctx.file, name.lower())
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
    attrs = dict({
        name: attr.label(allow_single_file = True)
        for name in [
            "coverage_config",
            "grcov",
            "grcov_config",
            "jq_bin",
            "jq_filter",
            "script",
            "template_base",
            "template_index",
            "template_macros",
            "toolshed_jq_root",
            "zstd_bin",
        ]
    }, source_root = attr.string(), source_glob = attr.string()),
)

def coverage_report(
        name,
        config,
        templates = None,
        source_root = "source",
        source_glob = "*.cc",
        zstd = Label("@zstd//:zstd_cli"),
        grcov = "@grcov//:grcov",
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
        jq_bin = _JQ,
        jq_filter = _MAIN,
        template_base = resolved_templates["base.html"],
        template_index = resolved_templates["index.html"],
        template_macros = resolved_templates["macros.html"],
        toolshed_jq_root = _MARKER,
        zstd_bin = zstd,
        source_root = source_root,
        source_glob = source_glob,
    )
    sh_binary(
        name = name,
        srcs = [":" + name + "_script"],
        data = [
            config,
            grcov,
            grcov_config,
            zstd,
            _JQ,
            _MODULES,
            _MARKER,
            _MAIN,
        ] + resolved_templates.values(),
        deps = [_RUNFILES],
        env = {
            "COVERAGE_CONFIG": "$(rlocationpath %s)" % config,
            "GRCOV": "$(rlocationpath %s)" % grcov,
            "GRCOV_CONFIG": "$(rlocationpath %s)" % grcov_config,
            "JQ_BIN": "$(rlocationpath %s)" % _JQ,
            "JQ_FILTER": "$(rlocationpath %s)" % _MAIN,
            "SOURCE_GLOB": source_glob,
            "SOURCE_ROOT": source_root,
            "TEMPLATE_BASE": "$(rlocationpath %s)" % resolved_templates["base.html"],
            "TEMPLATE_INDEX": "$(rlocationpath %s)" % resolved_templates["index.html"],
            "TEMPLATE_MACROS": "$(rlocationpath %s)" % resolved_templates["macros.html"],
            "TOOLSHED_JQ_ROOT": "$(rlocationpath %s)" % _MARKER,
            "ZSTD_BIN": "$(rlocationpath %s)" % zstd,
        },
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
