"""Test fixtures for dependency updater targets."""

def module_updater_fixture(name, args, out):
    output_source = "report.json" if "--report" in args else "MODULE.bazel"
    command = " ".join(args)
    native.genrule(
        name = name,
        srcs = [
            "testdata/module/MODULE.template.bazel",
            "testdata/module/deps.template.json",
            "testdata/module/report.bazelrc.template",
            "testdata/module/registry_bcr/REGISTRY_MARKER",
            "testdata/module/registry_bcr/modules/aspect_bazel_lib/metadata.json",
            "testdata/module/registry_bcr/modules/bazel_skylib/metadata.json",
            "testdata/module/registry_bcr/modules/protobuf/metadata.json",
            "testdata/module/registry_envoy/REGISTRY_MARKER",
            "testdata/module/registry_envoy/modules/protobuf/metadata.json",
            "testdata/module/registry_envoy/modules/sq/metadata.json",
            "//dependency:module-update.sh",
        ],
        outs = [out],
        tools = ["@buildifier//:buildozer", "@envoy_toolshed_jq//:jq"],
        # Action inputs are read-only under remote execution and `cp` preserves
        # mode, so the copied MODULE.bazel must be made writable before buildozer
        # edits it in place.
        cmd = """
set -euo pipefail
tmpdir="$$(mktemp -d)"
trap 'rm -rf "$$tmpdir"' EXIT
bcr_root="$$(dirname $(location testdata/module/registry_bcr/REGISTRY_MARKER))"
envoy_root="$$(dirname $(location testdata/module/registry_envoy/REGISTRY_MARKER))"
sed -e "s|__REGISTRY_BCR__|$$bcr_root|g" -e "s|__REGISTRY_ENVOY__|$$envoy_root|g" $(location testdata/module/deps.template.json) > "$$tmpdir/deps.json"
sed -e "s|__REGISTRY_BCR__|$$bcr_root|g" -e "s|__REGISTRY_ENVOY__|$$envoy_root|g" $(location testdata/module/report.bazelrc.template) > "$$tmpdir/.bazelrc"
cp $(location testdata/module/MODULE.template.bazel) "$$tmpdir/MODULE.bazel"
chmod u+w "$$tmpdir/MODULE.bazel"
# RUNFILES_DIR is buildozer's; the `rules_jq` launcher falls back to its own
# runfiles for keys missing there.
BUILD_WORKSPACE_DIRECTORY="$$tmpdir" RUNFILES_DIR=$(execpath @buildifier//:buildozer).runfiles JQ_BIN=$(execpath @envoy_toolshed_jq//:jq) BUILDOZER=$(execpath @buildifier//:buildozer) bash $(location //dependency:module-update.sh) "$$tmpdir/MODULE.bazel" "$$tmpdir/deps.json" --bazelrc="$$tmpdir/.bazelrc" %s >/dev/null
cp "$$tmpdir/%s" "$@"
""" % (command, output_source),
    )
