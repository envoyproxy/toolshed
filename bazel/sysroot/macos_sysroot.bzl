"""Rules for building the macOS sysroot packaging artifact."""

load("//:versions.bzl", "VERSIONS")

def _download_file_repo_impl(ctx):
    output = ctx.attr.output
    if ctx.attr.user_agent:
        # repository_ctx.download does not support custom headers.
        # Use curl when a user-agent override is required by the source host.
        result = ctx.execute([
            "bash",
            "-c",
            "set -euo pipefail; curl -fsSL -A \"$1\" \"$2\" -o \"$3\"; echo \"$4  $3\" | sha256sum -c -",
            "download-file",
            ctx.attr.user_agent,
            ctx.attr.url,
            output,
            ctx.attr.sha256,
        ])
        if result.return_code:
            fail("Failed to download {}: {}".format(ctx.attr.url, result.stderr))
    else:
        ctx.download(
            url = ctx.attr.url,
            output = output,
            sha256 = ctx.attr.sha256,
            executable = ctx.attr.executable,
        )
    if ctx.attr.executable:
        chmod_result = ctx.execute(["chmod", "+x", output])
        if chmod_result.return_code:
            fail("Failed to make {} executable: {}".format(output, chmod_result.stderr))

    if ctx.attr.filegroup == output:
        fail("filegroup name must differ from output file name ({})".format(output))

    ctx.file("BUILD.bazel", """
package(default_visibility = ["//visibility:public"])

exports_files(["{output}"])

filegroup(
    name = "{filegroup}",
    srcs = ["{output}"],
)
""".format(output = output, filegroup = ctx.attr.filegroup))

download_file_repo = repository_rule(
    implementation = _download_file_repo_impl,
    attrs = {
        "url": attr.string(mandatory = True),
        "sha256": attr.string(mandatory = True),
        "output": attr.string(mandatory = True),
        "filegroup": attr.string(mandatory = True),
        "user_agent": attr.string(default = ""),
        "executable": attr.bool(default = False),
    },
)

def setup_macos_sysroot_build():
    """Set up repos needed to build //sysroot:sysroot_macos_arm64."""
    if "pkgutil_linux_amd64" not in native.existing_rules():
        download_file_repo(
            name = "pkgutil_linux_amd64",
            url = VERSIONS["pkgutil"]["url"],
            sha256 = VERSIONS["pkgutil"]["sha256"],
            output = "pkgutil",
            filegroup = "pkgutil_bin",
            executable = True,
        )
    if "macos_sdk_pkg" not in native.existing_rules():
        download_file_repo(
            name = "macos_sdk_pkg",
            url = VERSIONS["macos_sdk_pkg"]["url"],
            sha256 = VERSIONS["macos_sdk_pkg"]["sha256"],
            output = "CLTools_macOSNMOS_SDK.pkg",
            filegroup = "sdk_pkg",
            user_agent = VERSIONS["macos_sdk_pkg"]["user_agent"],
        )

def _macos_sysroot_extract_impl(ctx):
    out_dir = ctx.actions.declare_directory(ctx.label.name)
    sdk_pkg = ctx.file.sdk_pkg
    manifest = ctx.file.manifest
    pkgutil = ctx.executable.pkgutil

    ctx.actions.run_shell(
        inputs = [sdk_pkg, manifest],
        tools = [pkgutil],
        outputs = [out_dir],
        arguments = [
            out_dir.path,
            pkgutil.path,
            sdk_pkg.path,
            manifest.path,
            ctx.attr.sdk_prefix,
        ],
        command = """
set -euo pipefail

out_dir="$1"
pkgutil="$2"
sdk_pkg="$3"
manifest="$4"
sdk_prefix="$5"

mkdir -p "${out_dir}/macos_arm64"
includes=()
while IFS= read -r line; do
  if [[ -z "${line}" ]]; then
    continue
  fi
  includes+=("--include" "${sdk_prefix}/${line}")
done < "${manifest}"

"${pkgutil}" "${includes[@]}" --strip-components 6 --expand-full "${sdk_pkg}" "${out_dir}/macos_arm64"

# Remove dangling symlinks. -xtype l matches symlinks whose target does not
# exist (GNU find semantics; resolves relative targets against the link's own
# directory, so valid relative links inside the tree are preserved).
echo "Scanning for dangling symlinks in ${out_dir}/macos_arm64 ..."
dangling=$(find "${out_dir}/macos_arm64" -xtype l)
if [[ -n "${dangling}" ]]; then
  echo "Removing dangling symlinks:"
  echo "${dangling}"
  find "${out_dir}/macos_arm64" -xtype l -delete
else
  echo "No dangling symlinks found."
fi
""",
        mnemonic = "MacosSysrootExtract",
        progress_message = "Extracting macOS sysroot from SDK package",
    )

    return [DefaultInfo(files = depset([out_dir]))]

macos_sysroot_extract = rule(
    implementation = _macos_sysroot_extract_impl,
    attrs = {
        "sdk_pkg": attr.label(
            mandatory = True,
            allow_single_file = True,
        ),
        "pkgutil": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            allow_files = True,
        ),
        "manifest": attr.label(
            mandatory = True,
            allow_single_file = True,
        ),
        "sdk_prefix": attr.string(mandatory = True),
    },
    doc = "Extracts a filtered macOS sysroot tree from Apple CLTools SDK package.",
)
