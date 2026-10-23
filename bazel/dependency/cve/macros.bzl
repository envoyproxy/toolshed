"""Reusable NVD CVE scanning and source-data updates."""

load("@aspect_bazel_lib//lib:write_source_files.bzl", "write_source_files")
load("@aspect_bazel_lib//lib:yq.bzl", "yq")
load("@envoy_toolshed_jq//:defs.bzl", "toolshed_jq")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")

_JQ = Label("@jq_toolchains//:resolved_toolchain")
_MODULES = Label("@envoy_toolshed_jq//:modules")
_ROOT = Label("@envoy_toolshed_jq//:modules_root.marker")
_MATCHER = Label("@envoy_toolshed_jq//:cve/matcher.jq")
_REPORT = Label("@envoy_toolshed_jq//:cve/report.jq")
_SCAN = Label("//dependency/cve:scan.sh")
_TEST = Label("//dependency/cve:test.sh")
_UPDATE = Label("//dependency/cve:update.sh")
_FETCH = Label("//dependency/cve:fetch")
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

def _scanned_impl(ctx):
    output = ctx.actions.declare_file(ctx.label.name + ".json")
    scanner = ctx.attr.scanner[DefaultInfo].files_to_run
    ctx.actions.run_shell(
        command = '"$1" > "$2"',
        arguments = [scanner.executable.path, output.path],
        tools = [scanner],
        outputs = [output],
        env = dict(ctx.attr.scanner[RunEnvironmentInfo].environment, **{
            "RUNFILES_DIR": scanner.executable.path + ".runfiles",
        }),
        execution_requirements = {"no-remote-exec": "1"},
        mnemonic = "CveScan",
    )
    return [DefaultInfo(files = depset([output]))]

_scanned = rule(
    implementation = _scanned_impl,
    attrs = {"scanner": attr.label(executable = True, cfg = "exec", mandatory = True)},
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
        env = dict(ctx.attr.updater[RunEnvironmentInfo].environment, **{
            "RUNFILES_DIR": updater.executable.path + ".runfiles",
        }),
        use_default_shell_env = True,
        execution_requirements = {
            "local": "1",
            "no-cache": "1",
            "no-remote": "1",
            "requires-network": "1",
        },
        mnemonic = "CveFetch",
        progress_message = "Fetching NVD CVE data for %{label}",
    )
    return [DefaultInfo(files = depset([output]))]

_fetch_data = rule(
    implementation = _fetch_data_impl,
    attrs = {
        "data": attr.label(allow_files = True),
        "updater": attr.label(executable = True, cfg = "exec", mandatory = True),
    },
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
        config: YAML containing start_year and ignored_cves.
        cve_data: Files (or label_flag) containing NVD 2.0 month JSON pages.
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
    for key, expression in [("ignored", ".ignored_cves // []"), ("start_year", ".start_year")]:
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
    data = [_JQ, _MODULES, _ROOT, _MATCHER, _REPORT, cve_data, ":" + name + "_data"]
    env = {
        "JQ_BIN": "$(rlocationpath %s)" % _JQ,
        "TOOLSHED_JQ_ROOT": "$(rlocationpath %s)" % _ROOT,
        "CVE_FILES": "$(rlocationpath :%s_data)" % name,
    }
    sh_binary(
        name = name,
        srcs = [_SCAN],
        data = data + [":" + name + "_deps", ":" + name + "_ignored"],
        deps = [_RUNFILES],
        env = dict(env, **{
            "CPE_DEPS": "$(rlocationpath :%s_deps)" % name,
            "CVES_IGNORED": "$(rlocationpath :%s_ignored)" % name,
            "JQ_CVE_MATCHER": "$(rlocationpath %s)" % _MATCHER,
        }),
        **common
    )
    _scanned(
        name = name + ".scanned",
        scanner = ":" + name,
        tags = ["manual", "no-remote-exec"],
        **common
    )
    sh_test(
        name = name + ".test",
        tags = ["manual"],
        srcs = [_TEST],
        data = [_JQ, _MODULES, _ROOT, _REPORT, ":" + name + ".scanned"],
        deps = [_RUNFILES],
        env = {
            "JQ_BIN": "$(rlocationpath %s)" % _JQ,
            "TOOLSHED_JQ_ROOT": "$(rlocationpath %s)" % _ROOT,
            "JQ_REPORT": "$(rlocationpath %s)" % _REPORT,
            "SCANNED": "$(rlocationpath :%s.scanned)" % name,
        },
        **common
    )
    update_kwargs = dict(helpers, target_compatible_with = target_compatible_with)
    sh_binary(
        name = name + "_fetcher",
        srcs = [_UPDATE],
        data = [cve_data, ":" + name + "_data", _FETCH, ":" + name + "_start_year"],
        deps = [_RUNFILES],
        env = {
            "CVE_FILES": "$(rlocationpath :%s_data)" % name,
            "FETCHER": "$(rlocationpath %s)" % _FETCH,
            "START_YEAR_PATH": "$(rlocationpath :%s_start_year)" % name,
        },
        **update_kwargs
    )
    _fetch_data(
        name = name + "_fetched",
        data = cve_data,
        updater = ":" + name + "_fetcher",
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
