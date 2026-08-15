"""Rules for building the darwin libcxx release artifact."""

# bsdtar (libarchive) from the aspect_bazel_lib toolchain. Unlike GNU tar,
# which forks the `xz` binary from $PATH to decompress .tar.xz, bsdtar
# decompresses in-process. This keeps the action hermetic: no dependency on
# xz-utils being installed in the execution environment, so it behaves
# identically on RBE workers and locally.
_TAR_TOOLCHAIN_TYPE = "@aspect_bazel_lib//lib:tar_toolchain_type"

def _libcxx_darwin_extract_impl(ctx):
    out_dir = ctx.actions.declare_directory(ctx.label.name)
    tarball = ctx.file.tarball
    strip_prefix = ctx.attr.strip_prefix
    install_name_tool = ctx.executable.install_name_tool
    bsdtar = ctx.toolchains[_TAR_TOOLCHAIN_TYPE]

    ctx.actions.run_shell(
        inputs = [tarball],
        tools = [install_name_tool, bsdtar.tarinfo.binary],
        outputs = [out_dir],
        env = bsdtar.tarinfo.default_env,
        command = """
set -euo pipefail

bsdtar="$1"
tarball="$2"
strip_prefix="$3"
out_dir="$4"
install_name_tool="$5"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

# Extract only the files we need from the macOS tarball. These paths are
# required, so a missing entry must fail the build rather than silently
# produce a partial output.
"$bsdtar" xf "$tarball" \
    --strip-components=1 \
    -C "$SCRATCH" \
    "$strip_prefix/include/c++/v1/__config_site" \
    "$strip_prefix/lib/libc++.1.0.dylib" \
    "$strip_prefix/lib/libc++abi.1.0.dylib"

for required in \
    "${SCRATCH}/include/c++/v1/__config_site" \
    "${SCRATCH}/lib/libc++.1.0.dylib" \
    "${SCRATCH}/lib/libc++abi.1.0.dylib"; do
    if [ ! -e "$required" ]; then
        echo "ERROR: expected path missing after extraction: $required" >&2
        exit 1
    fi
done

mkdir -p "${out_dir}/include" "${out_dir}/lib"

cp "${SCRATCH}/include/c++/v1/__config_site" "${out_dir}/include/__config_site"
# -L dereferences symlinks so we always copy a real file.
cp -L "${SCRATCH}/lib/libc++.1.0.dylib"    "${out_dir}/lib/libc++.1.0.dylib"
cp -L "${SCRATCH}/lib/libc++abi.1.0.dylib" "${out_dir}/lib/libc++abi.1.0.dylib"

"${install_name_tool}" -id /usr/lib/libc++.1.dylib   "${out_dir}/lib/libc++.1.0.dylib"
"${install_name_tool}" -id /usr/lib/libc++abi.dylib   "${out_dir}/lib/libc++abi.1.0.dylib"

ln -s libc++.1.0.dylib    "${out_dir}/lib/libc++.1.dylib"
ln -s libc++.1.0.dylib    "${out_dir}/lib/libc++.dylib"
ln -s libc++abi.1.0.dylib "${out_dir}/lib/libc++abi.1.dylib"
ln -s libc++abi.1.0.dylib "${out_dir}/lib/libc++abi.dylib"
""",
        arguments = [
            bsdtar.tarinfo.binary.path,
            tarball.path,
            strip_prefix,
            out_dir.path,
            install_name_tool.path,
        ],
        mnemonic = "DarwinLibcxxExtract",
        progress_message = "Extracting darwin libcxx from LLVM release",
    )

    return [DefaultInfo(files = depset([out_dir]))]

libcxx_darwin_extract = rule(
    implementation = _libcxx_darwin_extract_impl,
    attrs = {
        "tarball": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "The macOS-ARM64 LLVM tarball blob.",
        ),
        "strip_prefix": attr.string(
            mandatory = True,
            doc = "Archive strip prefix (e.g. 'LLVM-22.1.8-macOS-ARM64').",
        ),
        "install_name_tool": attr.label(
            executable = True,
            cfg = "exec",
            allow_files = True,
            mandatory = True,
            doc = "llvm-install-name-tool executable.",
        ),
    },
    toolchains = [_TAR_TOOLCHAIN_TYPE],
    doc = "Extracts and patches darwin libcxx files from an LLVM macOS tarball.",
)
