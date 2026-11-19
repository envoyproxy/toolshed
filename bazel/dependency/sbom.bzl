"""Software bills of materials (SBOMs) from dependency metadata."""

load("@envoy_toolshed_jq//:defs.bzl", "toolshed_jq")

_FILTER = """
import "sbom/cyclonedx" as cdx;
(if $ARGS.named.reachability then cdx::reachable($ARGS.named.reachability[0]) else . end)
| cdx::bom(
    {name: $name, version: ($version | gsub("\\\\s"; ""))}
    + (if $purl != "" then {purl: ($purl | gsub("{version}"; ($version | gsub("\\\\s"; ""))))} else {} end)
    + (if $description != "" then {description: $description} else {} end);
    {
      build_categories: ($build_categories | fromjson),
      build_time: $build_time,
      category_key: $category_key,
    })
"""

def cyclonedx_sbom(
        name,
        dependencies,
        subject,
        version = None,
        version_file = None,
        reachability = None,
        purl = None,
        description = None,
        build_categories = [],
        build_time = "omit",
        category_key = "use_category",
        out = None,
        **kwargs):
    """Generate a CycloneDX (1.5, JSON) SBOM from dependency metadata.

    Each dependency with a version becomes a component, with what its metadata gives of a
    package URL, CPE, license, digest and download location (see the `sbom/cyclonedx` jq module).
    The output is deterministic: it has no serial number or timestamp.

    Args:
        name: Name of the target. The SBOM is written to `out`.
        dependencies: Label of the dependency JSON: an object of dependencies keyed by name, as
            for `cve_scan`.
        subject: Name of what the SBOM is for, eg `envoy`.
        version: Version of the subject. One of `version` or `version_file` is required.
        version_file: Label of a file containing the version of the subject.
        reachability: Optional label of a reachability map (`dependency_reachability`). If set,
            only the dependencies it has as reached in production are listed.
        purl: Optional package URL of the subject; `{version}` is replaced with the version.
            Without one a `pkg:generic` URL is made from the name and version.
        description: Optional description of the subject.
        build_categories: Categories that mark a dependency as only used to build: one with any
            of them is build-time, whatever others it has. Empty (the default), none are.
        build_time: What to do with build-time dependencies: `omit` them (the default), list them
            with the `excluded` scope (`excluded`), or list them as any other (`include`).
        category_key: The field of a dependency with its categories, `use_category` by default.
        out: Output file, defaults to `<name>.cdx.json`.
        **kwargs: Other common named parameters such as `tags` or `visibility`.
    """
    if bool(version) == bool(version_file):
        fail("cyclonedx_sbom: exactly one of `version` or `version_file` is required")
    if build_time not in ["omit", "excluded", "include"]:
        fail("cyclonedx_sbom: `build_time` must be one of omit, excluded or include")
    args = [
        "--arg",
        "name",
        subject,
        "--arg",
        "purl",
        purl or "",
        "--arg",
        "description",
        description or "",
        "--arg",
        "build_categories",
        json.encode(build_categories),
        "--arg",
        "build_time",
        build_time,
        "--arg",
        "category_key",
        category_key,
    ]
    data = []
    if version_file:
        args += ["--rawfile", "version", "$(location %s)" % version_file]
        data.append(version_file)
    else:
        args += ["--arg", "version", version]
    if reachability:
        args += ["--slurpfile", "reachability", "$(location %s)" % reachability]
        data.append(reachability)
    toolshed_jq(
        name = name,
        srcs = [dependencies],
        out = out or name + ".cdx.json",
        filter = _FILTER,
        args = args,
        data = data,
        **kwargs
    )
