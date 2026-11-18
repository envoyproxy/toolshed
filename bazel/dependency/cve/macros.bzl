"""Reusable CVE scanning (NVD and CVE Program data) and source-data updates."""

load("@aspect_bazel_lib//lib:write_source_files.bzl", "write_source_files")
load("@aspect_bazel_lib//lib:yq.bzl", "yq")
load("@envoy_toolshed_jq//:defs.bzl", "toolshed_jq")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")

# jq with the toolshed modules importable.
_JQ = Label("@envoy_toolshed_jq//:jq")
_MATCHER = Label("@envoy_toolshed_jq//:cve/matcher.jq")
_CNA_MATCHER = Label("@envoy_toolshed_jq//:cve/cna_matcher.jq")
_NVD_SCAN = Label("@envoy_toolshed_jq//:cve/nvd_scan.jq")
_MERGE = Label("@envoy_toolshed_jq//:cve/merge.jq")
_REPORT = Label("@envoy_toolshed_jq//:cve/report.jq")
_SCAN = Label("//dependency/cve:scan.sh")
_TEST = Label("//dependency/cve:test.sh")
_UPDATE = Label("//dependency/cve:update.sh")
_FETCH = Label("//dependency/cve:fetch")
_CVELIST_FETCH = Label("//dependency/cve:cvelist_fetch")
_RUNFILES = Label("@bazel_tools//tools/bash/runfiles")

def _data_manifest_impl(ctx):
    manifest = ctx.actions.declare_file(ctx.label.name + ".txt")
    paths = []
    for file in ctx.files.data:
        if file.extension != "json":
            continue
        path = file.short_path
        paths.append(path[3:] if path.startswith("../") else ctx.workspace_name + "/" + path)
    ctx.actions.write(manifest, "\n".join(sorted(paths)) + ("\n" if paths else ""))
    return [DefaultInfo(files = depset([manifest]))]

_data_manifest = rule(
    implementation = _data_manifest_impl,
    attrs = {"data": attr.label(allow_files = True)},
)

def _rlocationpath(ctx, target):
    """The runfiles path of a target: of its executable if it has one, else of its one file."""
    info = target[DefaultInfo]
    executable = info.files_to_run.executable if info.files_to_run else None
    files = [executable] if executable else info.files.to_list()
    if len(files) != 1:
        fail("Expected one file for %s, got %d" % (target.label, len(files)))
    path = files[0].short_path
    return path[3:] if path.startswith("../") else ctx.workspace_name + "/" + path

def _tool_env(ctx, tool):
    """The environment to run `tool` with: the runfiles paths that its own `env` gives it.

    These are worked out here, and not read from the tool's `RunEnvironmentInfo` (with Bazel 7 an
    `sh_binary` does not provide it) or expanded with `ctx.expand_location` (with Bazel 7 that
    takes every default output of an executable, so fails for a `py_binary`).
    """
    env = {key: _rlocationpath(ctx, target) for target, key in ctx.attr.env.items()}
    env["RUNFILES_DIR"] = tool.executable.path + ".runfiles"
    return env

# The targets that a tool's `env` gives it the runfiles paths of, to the name of each variable.
_TOOL_ENV_ATTRS = {
    "env": attr.label_keyed_string_dict(allow_files = True, cfg = "exec"),
}

def _env(targets):
    """The `env` of a tool, from the `env` of the rule that runs it (see `_TOOL_ENV_ATTRS`)."""
    return {key: "$(rlocationpath %s)" % target for target, key in targets.items()}

def _scanned_impl(ctx):
    output = ctx.actions.declare_file(ctx.label.name + ".json")
    scanner = ctx.attr.scanner[DefaultInfo].files_to_run
    ctx.actions.run_shell(
        command = '"$1" > "$2"',
        arguments = [scanner.executable.path, output.path],
        tools = [scanner],
        outputs = [output],
        env = _tool_env(ctx, scanner),
        execution_requirements = {"no-remote-exec": "1"},
        mnemonic = "CveScan",
    )
    return [DefaultInfo(files = depset([output]))]

_scanned = rule(
    implementation = _scanned_impl,
    attrs = dict(_TOOL_ENV_ATTRS, **{
        "scanner": attr.label(executable = True, cfg = "exec", mandatory = True),
    }),
)

def _fetch_data_impl(ctx):
    output = ctx.actions.declare_directory(ctx.label.name)
    updater = ctx.attr.updater[DefaultInfo].files_to_run
    ctx.actions.run(
        executable = updater,
        arguments = [output.path],
        inputs = ctx.files.data,
        outputs = [output],
        tools = [updater],
        env = _tool_env(ctx, updater),
        use_default_shell_env = True,
        execution_requirements = {
            "local": "1",
            "no-cache": "1",
            "no-remote": "1",
            "requires-network": "1",
        },
        mnemonic = "CveFetch",
        progress_message = "Fetching CVE data for %{label}",
    )
    return [DefaultInfo(files = depset([output]))]

_fetch_data = rule(
    implementation = _fetch_data_impl,
    attrs = dict(_TOOL_ENV_ATTRS, **{
        "data": attr.label(allow_files = True),
        "updater": attr.label(executable = True, cfg = "exec", mandatory = True),
    }),
)

def cve_scan(
        name,
        deps,
        config,
        cve_data,
        cve_data_dir = "cve_data",
        visibility = None,
        target_compatible_with = ["@platforms//os:linux"]):
    """Create scan, test and source-data update targets.

    Args:
        name: Scan binary name; also prefixes generated helpers.
        deps: Raw dependency JSON, keyed by dependency name.
        config: YAML containing start_year, ignored_cves and optionally
            sources (default `[nvd, cna]`).
        cve_data: Files (or label_flag) containing NVD 2.0 month JSON pages, and
            optionally CVE Program (cvelistV5) month files under `cvelist/`.
        cve_data_dir: Package-relative directory written by <name>.update.
        visibility: Visibility of generated targets.
        target_compatible_with: Update target constraints; defaults to Linux.
    """
    common = {"visibility": visibility}
    helpers = dict(common, tags = ["manual"])
    toolshed_jq(
        name = name + "_deps",
        srcs = [deps],
        out = name + "_deps.json",
        filter = 'import "cve/utils" as utils; utils::parse_deps(.)',
        **helpers
    )
    for key, expression in [
        ("ignored", ".ignored_cves // []"),
        ("start_year", ".start_year"),
        ("sources", '.sources // ["nvd", "cna"]'),  # a list, or a bare string for one source
    ]:
        yq(
            name = name + "_" + key,
            srcs = [config],
            outs = [name + "_" + key + ".json"],
            expression = expression,
            args = ["-o=json"],
            **helpers
        )
    _data_manifest(
        name = name + "_data",
        data = cve_data,
        **helpers
    )
    data = [_JQ, _MATCHER, _CNA_MATCHER, _NVD_SCAN, _MERGE, _REPORT, cve_data, ":" + name + "_data"]
    scan_env = {
        _JQ: "JQ_BIN",
        ":" + name + "_data": "CVE_FILES",
        ":" + name + "_deps": "CPE_DEPS",
        ":" + name + "_ignored": "CVES_IGNORED",
        ":" + name + "_sources": "CVES_SOURCES",
        _MATCHER: "JQ_CVE_MATCHER",
        _CNA_MATCHER: "JQ_CNA_MATCHER",
        _NVD_SCAN: "JQ_NVD_SCAN",
        _MERGE: "JQ_MERGE",
    }
    sh_binary(
        name = name,
        srcs = [_SCAN],
        data = data + [":" + name + "_deps", ":" + name + "_ignored", ":" + name + "_sources"],
        deps = [_RUNFILES],
        env = _env(scan_env),
        **common
    )
    _scanned(
        name = name + ".scanned",
        scanner = ":" + name,
        env = scan_env,
        tags = ["manual", "no-remote-exec"],
        **common
    )
    sh_test(
        name = name + ".test",
        tags = ["manual"],
        srcs = [_TEST],
        data = [_JQ, _REPORT, ":" + name + ".scanned"],
        deps = [_RUNFILES],
        env = {
            "JQ_BIN": "$(rlocationpath %s)" % _JQ,
            "JQ_REPORT": "$(rlocationpath %s)" % _REPORT,
            "SCANNED": "$(rlocationpath :%s.scanned)" % name,
        },
        **common
    )
    update_kwargs = dict(helpers, target_compatible_with = target_compatible_with)
    fetch_env = {
        ":" + name + "_data": "CVE_FILES",
        _FETCH: "FETCHER",
        _CVELIST_FETCH: "CVELIST_FETCHER",
        ":" + name + "_start_year": "START_YEAR_PATH",
    }
    sh_binary(
        name = name + "_fetcher",
        srcs = [_UPDATE],
        data = [cve_data] + fetch_env.keys(),
        deps = [_RUNFILES],
        env = _env(fetch_env),
        **update_kwargs
    )
    _fetch_data(
        name = name + "_fetched",
        data = cve_data,
        updater = ":" + name + "_fetcher",
        env = fetch_env,
        tags = ["manual", "local", "no-cache", "no-remote", "requires-network"],
        target_compatible_with = target_compatible_with,
        **common
    )
    write_source_files(
        name = name + ".update",
        files = {cve_data_dir: ":" + name + "_fetched"},
        diff_test = False,
        check_that_out_file_exists = False,
        **update_kwargs
    )
