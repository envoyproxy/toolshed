"""Macros for dependency update utilities."""

load("@aspect_bazel_lib//lib:jq.bzl", "jq")
load("@aspect_bazel_lib//lib:write_source_files.bzl", "write_source_files")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("//dependency:registry.bzl", "registry_bazelrc", "repo_registry")

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
    """Create a shell-based dependency updater binary.

    Args:
        name: Name of the generated target.
        dependencies: Label for the dependency data consumed by the updater.
        version_file: Label for the file updated in place.
        jq_toolchain: jq toolchain target used by the updater.
        update_script: Shell script implementing the update logic.
        post_script: Optional script run after a version update.
        data: Additional runtime data dependencies.
        deps: Additional target dependencies.
        dep_search: Optional search string for dependency entries.
        sha_search: Optional search string for sha entries.
        version_search: Optional search string for version entries.
        repo_selector: Optional selector for repo names.
        sha_selector: Optional selector for sha values.
        url_selector: Optional selector for URLs.
        version_path_replace: Optional replacement for version paths.
        version_selector: Optional selector for version values.
        toolchains: Additional toolchains required by the updater.
        pydict: Whether to use Python dict search defaults.
        **kwargs: Forwarded to sh_binary.
    """
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
        data.append(post_script)
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

def registry_updater(
        name,
        bazelrc,
        repo = "https://github.com/envoyproxy/bazel-registry.git",
        url = "https://raw.githubusercontent.com/envoyproxy/bazel-registry",
        ref = "main",
        visibility = None,
        **kwargs):
    """Rewrite the registry pin in a bazelrc file.

    Args:
        name: Name of the generated target.
        bazelrc: Label for the bazelrc file to rewrite.
        repo: Git repository used to resolve the current registry SHA.
        url: Raw content base URL for the registry.
        ref: Git ref to resolve from the registry repository.
        visibility: Optional visibility for the generated target.
        **kwargs: Forwarded to write_source_files.
    """
    helper_tags = ["manual"] + kwargs.pop("tags", [])
    target_compatible_with = kwargs.pop(
        "target_compatible_with",
        ["@platforms//os:linux"],
    )

    repo_registry(
        name = name + "_resolved",
        ref = ref,
        repo = repo,
        tags = helper_tags,
        target_compatible_with = target_compatible_with,
        url = url,
    )
    registry_bazelrc(
        name = name + "_bazelrc",
        bazelrc = bazelrc,
        registry = ":" + name + "_resolved",
        tags = helper_tags,
        target_compatible_with = target_compatible_with,
        url = url,
    )

    if visibility != None:
        kwargs["visibility"] = visibility

    write_source_files(
        name = name,
        check_that_out_file_exists = False,
        diff_test = False,
        files = {bazelrc: ":" + name + "_bazelrc"},
        tags = helper_tags,
        target_compatible_with = target_compatible_with,
        **kwargs
    )

def module_deps_json(
        name,
        lockfile,
        module_file,
        buildozer = "@buildifier//:buildozer",
        visibility = None):
    """Generate dependency JSON from MODULE.bazel and MODULE.bazel.lock.

    Args:
        name: Name of the generated target.
        lockfile: Label for the lockfile to read.
        module_file: Label for the MODULE.bazel file to read declared deps from.
        buildozer: buildozer binary used to read bazel_dep declarations.
        visibility: Optional target visibility.
    """
    native.genrule(
        name = name + "_declared",
        srcs = [module_file],
        outs = [name + ".declared.txt"],
        tools = [buildozer],
        cmd = """
set -euo pipefail
err="$(@D)/%s.declared.err"
status=0
RUNFILES_DIR="$(execpath %s).runfiles" "$(execpath %s)" 'print name version' "$(location %s):%%bazel_dep" > "$@" 2>"$$err" || status=$$?
if [ "$$status" -eq 3 ]; then
  : > "$@"
elif [ "$$status" -ne 0 ]; then
  cat "$$err" >&2
  exit "$$status"
fi
rm -f "$$err"
""" % (name, buildozer, buildozer, module_file),
    )

    native.genrule(
        name = name + "_overridden",
        srcs = [module_file],
        outs = [name + ".overridden.txt"],
        tools = [buildozer],
        cmd = """
set -euo pipefail
: > "$@"
err="$(@D)/%s.overridden.err"
status=0
RUNFILES_DIR="$(execpath %s).runfiles" "$(execpath %s)" 'print module_name' "$(location %s):%%local_path_override" >> "$@" 2>"$$err" || status=$$?
if [ "$$status" -ne 0 ] && [ "$$status" -ne 3 ]; then
  cat "$$err" >&2
  exit "$$status"
fi
status=0
RUNFILES_DIR="$(execpath %s).runfiles" "$(execpath %s)" 'print module_name' "$(location %s):%%git_override" >> "$@" 2>"$$err" || status=$$?
if [ "$$status" -ne 0 ] && [ "$$status" -ne 3 ]; then
  cat "$$err" >&2
  exit "$$status"
fi
status=0
RUNFILES_DIR="$(execpath %s).runfiles" "$(execpath %s)" 'print module_name' "$(location %s):%%archive_override" >> "$@" 2>"$$err" || status=$$?
if [ "$$status" -ne 0 ] && [ "$$status" -ne 3 ]; then
  cat "$$err" >&2
  exit "$$status"
fi
rm -f "$$err"
""" % (
            name,
            buildozer,
            buildozer,
            module_file,
            buildozer,
            buildozer,
            module_file,
            buildozer,
            buildozer,
            module_file,
        ),
    )

    jq(
        name = name,
        srcs = [lockfile],
        out = name + ".json",
        filter_file = "//dependency:module_deps_json.jq",
        expand_args = True,
        args = [
            "--rawfile",
            "declared",
            "$(location :%s_declared)" % name,
            "--rawfile",
            "overridden",
            "$(location :%s_overridden)" % name,
            "-L",
            "dependency",
        ],
        data = [
            ":" + name + "_declared",
            ":" + name + "_overridden",
            "//dependency:jq_libs",
        ],
        visibility = visibility,
    )

def module_updater(
        name,
        dependencies,
        module_file,
        bazelrc = None,
        registries = None,
        jq_toolchain = "@jq_toolchains//:resolved_toolchain",
        update_script = "@envoy_toolshed//dependency:module-update.sh",
        buildozer = "@buildifier//:buildozer",
        data = None,
        deps = None,
        toolchains = None,
        visibility = None,
        **kwargs):
    """Create a bzlmod dependency updater runnable.

    Args:
        name: Name of the generated target.
        dependencies: Label for the dependency JSON input.
        module_file: Label for the MODULE.bazel file to update.
        bazelrc: Optional bazelrc file used to discover registries.
        registries: Optional explicit list of registries.
        jq_toolchain: jq toolchain target used by the updater.
        update_script: Shell script implementing the updater.
        buildozer: buildozer binary used to rewrite MODULE.bazel.
        data: Additional runtime data dependencies.
        deps: Additional target dependencies.
        toolchains: Additional toolchains required by the updater.
        visibility: Optional target visibility.
        **kwargs: Forwarded to sh_binary.
    """
    if not bazelrc and not registries:
        fail("module_updater requires either bazelrc or registries")

    toolchains = [jq_toolchain] + (toolchains or [])
    deps = deps or []
    data = (data or []) + [
        jq_toolchain,
        update_script,
        buildozer,
        dependencies,
        module_file,
        "//dependency:jq_libs",
        "//dependency:version.jq",
    ]
    env = {
        "JQ_BIN": "$(rootpath %s)" % jq_toolchain,
        "BUILDOZER": "$(rootpath %s)" % buildozer,
        "MODULE_UPDATER_JQ_DIR": "$(rootpath //dependency:version.jq)",
    }
    args = [
        "$(location %s)" % module_file,
        "$(location %s)" % dependencies,
    ]

    if bazelrc:
        data.append(bazelrc)
        env["MODULE_UPDATER_BAZELRC"] = "$(location %s)" % bazelrc
    if registries:
        env["MODULE_UPDATER_REGISTRIES"] = "\n".join(registries)

    if visibility != None:
        kwargs["visibility"] = visibility

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
