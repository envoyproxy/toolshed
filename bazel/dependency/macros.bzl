load("@aspect_bazel_lib//lib:write_source_files.bzl", "write_source_files")
load("@bazel_skylib//rules:common_settings.bzl", "bool_flag", "string_list_flag")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@envoy_toolshed_jq//:defs.bzl", "toolshed_jq")
load("//dependency:registry.bzl", "flag_json", "run_registry_update")

def updater(
        name,
        dependencies,
        version_file,
        jq_toolchain = "@jq_toolchains//:resolved_toolchain",
        update_script = "@envoy_toolshed//dependency:bazel-update.sh",
        post_script = None,
        data = None,
        deps = None,
        dep_search = None,
        sha_search = None,
        version_search = None,
        repo_selector = None,
        sha_selector = None,
        url_selector = None,
        version_path_replace = None,
        version_selector = None,
        toolchains = None,
        pydict = False,
        **kwargs):
    toolchains = [jq_toolchain] + (toolchains or [])
    deps = deps or []
    data = (data or []) + [
        jq_toolchain,
        update_script,
        dependencies,
        version_file,
    ]
    args = [
        "$(location %s)" % version_file,
        "$(location %s)" % dependencies,
    ]
    env = {"JQ_BIN": "$(rootpath %s)" % jq_toolchain}
    if pydict:
        env["DEP_SEARCH"] = "__DEP__ = dict("
        env["SHA_SEARCH"] = "sha256 = \"__EXISTING_SHA__\","
        env["VERSION_SEARCH"] = "version = \"__EXISTING_VERSION__\","

    if dep_search:
        env["DEP_SEARCH"] = dep_search
    if sha_search:
        env["SHA_SEARCH"] = sha_search
    if version_search:
        env["VERSION_SEARCH"] = version_search
    if repo_selector:
        env["REPO_SELECTOR"] = repo_selector
    if sha_selector:
        env["SHA_SELECTOR"] = sha_selector
    if url_selector:
        env["URL_SELECTOR"] = url_selector
    if version_path_replace:
        env["VERSION_PATH_REPLACE"] = version_path_replace
    if version_selector:
        env["VERSION_SELECTOR"] = version_selector

    if post_script:
        data += [post_script]
        env["VERSION_UPDATE_POST_SCRIPT"] = "$(location %s)" % post_script

    sh_binary(
        name = name,
        srcs = [update_script],
        data = data,
        env = env,
        args = args,
        deps = deps,
        toolchains = toolchains,
        **kwargs
    )

def _repo_path(label):
    parsed = Label(label)
    if parsed.workspace_name:
        fail("registry_updater only supports main-workspace files: {}".format(label))
    if parsed.package:
        return "{}/{}".format(parsed.package, parsed.name)
    return parsed.name

def _shared_kwargs(kwargs):
    shared = {}
    for key in ["tags", "testonly"]:
        if key in kwargs:
            shared[key] = kwargs[key]
    return shared

def _public_kwargs(kwargs):
    shared = _shared_kwargs(kwargs)
    if "visibility" in kwargs:
        shared["visibility"] = kwargs["visibility"]
    return shared

def _raw_file_json(name, src, path, **kwargs):
    toolshed_jq(
        name = name,
        srcs = [src],
        out = "{}.json".format(name),
        args = [
            "--raw-input",
            "--slurp",
            "--arg",
            "path",
            path,
        ],
        filter = "{($path): .}",
        **kwargs
    )

def _merge_json(name, srcs, **kwargs):
    toolshed_jq(
        name = name,
        srcs = srcs,
        out = "{}.json".format(name),
        args = ["--slurp"],
        filter = "add",
        **kwargs
    )

def registry_updater(
        name,
        bazelrc_files,
        module_files,
        version_file,
        registry_repo = "https://github.com/envoyproxy/bazel-registry",
        registry_branch = "main",
        registry_url_prefix = "https://raw.githubusercontent.com/envoyproxy/bazel-registry/",
        **kwargs):
    shared_kwargs = _shared_kwargs(kwargs)
    public_kwargs = _public_kwargs(kwargs)
    bazelrc_paths = [_repo_path(label) for label in bazelrc_files]
    module_paths = [_repo_path(label) for label in module_files]
    snapshot_repo = "@{}_snapshot".format(name)
    snapshot_info = "{}//:info".format(snapshot_repo)
    snapshot_index = "{}//:index".format(snapshot_repo)

    bazelrc_jsons = []
    for i, src in enumerate(bazelrc_files):
        target = "{}.bazelrc_file_{}".format(name, i)
        _raw_file_json(target, src, bazelrc_paths[i], **shared_kwargs)
        bazelrc_jsons.append(":{}".format(target))
    _merge_json("{}.bazelrc_files".format(name), bazelrc_jsons, **shared_kwargs)

    module_jsons = []
    for i, src in enumerate(module_files):
        target = "{}.module_file_{}".format(name, i)
        _raw_file_json(target, src, module_paths[i], **shared_kwargs)
        module_jsons.append(":{}".format(target))
    _merge_json("{}.module_files".format(name), module_jsons, **shared_kwargs)

    toolshed_jq(
        name = "{}.version".format(name),
        srcs = [version_file],
        out = "{}.version.json".format(name),
        args = ["--raw-input", "--slurp"],
        filter = "{version: (rtrimstr(\"\\n\"))}",
        **shared_kwargs
    )

    string_list_flag(
        name = "{}.set".format(name),
        build_setting_default = [],
        visibility = ["//visibility:public"],
    )
    flag_json(
        name = "{}.set_json".format(name),
        flag = ":{}.set".format(name),
        **shared_kwargs
    )
    toolshed_jq(
        name = "{}.overrides".format(name),
        srcs = [":{}.set_json".format(name)],
        out = "{}.overrides.json".format(name),
        filter = "import \"registry\" as registry; registry::overrides_from_flag",
        **shared_kwargs
    )

    bool_flag(
        name = "{}.check_only".format(name),
        build_setting_default = False,
        visibility = ["//visibility:public"],
    )
    flag_json(
        name = "{}.check_only_json".format(name),
        flag = ":{}.check_only".format(name),
        **shared_kwargs
    )

    toolshed_jq(
        name = "{}.current".format(name),
        srcs = [":{}.bazelrc_files".format(name)],
        out = "{}.current.json".format(name),
        args = [
            "--argjson",
            "paths",
            json.encode(bazelrc_paths),
            "--arg",
            "url_prefix",
            registry_url_prefix,
        ],
        filter = """
import "registry" as registry;
{files: ., paths: $paths, url_prefix: $url_prefix} | registry::bazelrc_hash
""",
        **shared_kwargs
    )

    toolshed_jq(
        name = "{}.pins".format(name),
        srcs = [":{}.module_files".format(name)],
        out = "{}.pins.json".format(name),
        args = [
            "--argjson",
            "paths",
            json.encode(module_paths),
        ],
        filter = """
import "registry" as registry;
{files: ., paths: $paths} | registry::module_pins
""",
        **shared_kwargs
    )

    toolshed_jq(
        name = "{}.exists".format(name),
        srcs = [
            ":{}.pins".format(name),
            snapshot_index,
        ],
        out = "{}.exists.json".format(name),
        args = ["--slurp"],
        filter = "import \"registry\" as registry; registry::exists",
        **shared_kwargs
    )

    toolshed_jq(
        name = "{}.plan".format(name),
        srcs = [
            ":{}.pins".format(name),
            ":{}.exists".format(name),
            snapshot_index,
            ":{}.current".format(name),
            snapshot_info,
            ":{}.overrides".format(name),
        ],
        out = "{}.plan.json".format(name),
        args = ["--slurp"],
        filter = "import \"registry\" as registry; registry::plan",
        **public_kwargs
    )

    toolshed_jq(
        name = "{}.check".format(name),
        srcs = [
            ":{}.current".format(name),
            snapshot_info,
            ":{}.version".format(name),
            ":{}.check_only_json".format(name),
        ],
        out = "{}.check.json".format(name),
        args = [
            "--slurp",
            "--arg",
            "repo",
            registry_repo,
            "--arg",
            "branch",
            registry_branch,
        ],
        filter = "import \"registry\" as registry; registry::check",
        **shared_kwargs
    )

    toolshed_jq(
        name = "{}.report".format(name),
        srcs = [":{}.plan".format(name)],
        out = "{}.report.json".format(name),
        filter = "del(.edits, .errors)",
        **public_kwargs
    )

    toolshed_jq(
        name = "{}.edits".format(name),
        srcs = [
            ":{}.plan".format(name),
            ":{}.current".format(name),
            ":{}.bazelrc_files".format(name),
            ":{}.module_files".format(name),
        ],
        out = "{}.edits.json".format(name),
        args = [
            "--slurp",
            "--arg",
            "url_prefix",
            registry_url_prefix,
        ],
        filter = "import \"registry\" as registry; registry::apply",
        **public_kwargs
    )

    toolshed_jq(
        name = "{}.check_ok".format(name),
        srcs = [
            ":{}.check".format(name),
            ":{}.plan".format(name),
        ],
        out = "{}.check_ok.json".format(name),
        args = ["--slurp"],
        filter = """
if (map(.errors // []) | add | length) > 0 then
  error(map(.errors // []) | add | join("\\n"))
else
  .
end
""",
        **public_kwargs
    )

    toolshed_jq(
        name = "{}.messages".format(name),
        srcs = [":{}.check".format(name)],
        out = "{}.messages.txt".format(name),
        args = ["-r"],
        filter = ".messages[]?",
        **public_kwargs
    )

    toolshed_jq(
        name = "{}.report_text".format(name),
        srcs = [":{}.report".format(name)],
        out = "{}.report.txt".format(name),
        args = ["-r"],
        filter = "import \"registry\" as registry; registry::render_report",
        **public_kwargs
    )

    write_targets = {}
    for i, src in enumerate(bazelrc_files):
        path = bazelrc_paths[i]
        target = "{}.write_bazelrc_{}".format(name, i)
        toolshed_jq(
            name = target,
            srcs = [
                ":{}.check_ok".format(name),
                snapshot_info,
                ":{}.bazelrc_file_{}".format(name, i),
            ],
            out = "{}.txt".format(target),
            args = [
                "--slurp",
                "-r",
                "--arg",
                "path",
                path,
                "--arg",
                "url_prefix",
                registry_url_prefix,
            ],
            filter = """
import "registry" as registry;
(.[1].hash) as $hash
| (.[2]) as $files
| ({files: $files, paths: [$path], url_prefix: $url_prefix, hash: $hash} | registry::apply_hash)[$path]
""",
            **shared_kwargs
        )
        write_targets[path] = ":{}".format(target)

    for i, src in enumerate(module_files):
        path = module_paths[i]
        target = "{}.write_module_{}".format(name, i)
        toolshed_jq(
            name = target,
            srcs = [
                ":{}.check_ok".format(name),
                ":{}.plan".format(name),
                ":{}.module_file_{}".format(name, i),
            ],
            out = "{}.txt".format(target),
            args = [
                "--slurp",
                "-r",
                "--arg",
                "path",
                path,
            ],
            filter = """
import "registry" as registry;
(.[1].edits | map(select(.file == $path))) as $edits
| (.[2]) as $files
| (({files: $files, edits: $edits} | registry::apply_edits)[$path] // $files[$path])
""",
            **shared_kwargs
        )
        write_targets[path] = ":{}".format(target)

    write_source_files(
        name = "{}.write".format(name),
        files = write_targets,
        check_that_out_file_exists = False,
        diff_test = False,
        verbosity = "quiet",
        **public_kwargs
    )

    run_registry_update(
        name = name,
        writer = ":{}.write".format(name),
        messages = ":{}.messages".format(name),
        report = ":{}.report_text".format(name),
        **kwargs
    )
