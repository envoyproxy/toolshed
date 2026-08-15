"""Repository rule and extraction rule for prebuilt LLVM libcxx artifacts."""

load("//:versions.bzl", "SUPPORTED_ARCHES", "VERSIONS")

_TAR_TOOLCHAIN_TYPE = "@aspect_bazel_lib//lib:tar_toolchain_type"

def _llvm_prebuilt_impl(ctx):
    ctx.download(
        url = ctx.attr.url,
        output = "llvm.tar.xz",
        sha256 = ctx.attr.sha256,
    )
    ctx.file("BUILD.bazel", 'exports_files(["llvm.tar.xz"])\n')
    return ctx.repo_metadata(reproducible = True)

llvm_prebuilt = repository_rule(
    implementation = _llvm_prebuilt_impl,
    attrs = {
        "sha256": attr.string(mandatory = True),
        "strip_prefix": attr.string(mandatory = True),
        "url": attr.string(mandatory = True),
    },
)

def setup_llvm_prebuilt():
    """Set up llvm_libcxx_* repos used by WORKSPACE and bzlmod."""
    for arch in SUPPORTED_ARCHES:
        repo_name = "llvm_libcxx_%s" % arch
        if repo_name in native.existing_rules():
            continue
        config = VERSIONS[repo_name]
        llvm_prebuilt(
            name = repo_name,
            sha256 = config["sha256"],
            strip_prefix = config["strip_prefix"].format(**config),
            url = config["url"].format(**config),
        )

_LLVM_PREBUILT_EXTRACT_SCRIPT = """
set -euo pipefail
BSDTAR="$1"
TARBALL="$2"
STRIP_PREFIX="$3"
TRIPLE="$4"
OUT_LIBCXX="$5"
OUT_LIBCXXABI="$6"
OUT_LIBUNWIND="$7"
OUT_COMPILER_RT="$8"
OUT_CONFIG_SITE="$9"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

strip_prefix="${STRIP_PREFIX%/}"
compiler_rt_member=""
compiler_rt_count=0

while IFS= read -r member; do
    case "$member" in
        "$strip_prefix"/lib/clang/*/lib/"$TRIPLE"/libclang_rt.builtins.a)
            compiler_rt_member="$member"
            compiler_rt_count=$((compiler_rt_count + 1))
            ;;
    esac
done < <("$BSDTAR" tf "$TARBALL")

if [ "$compiler_rt_count" -ne 1 ]; then
    echo "ERROR: expected exactly one compiler_rt member for '$TRIPLE', found $compiler_rt_count" >&2
    exit 1
fi

"$BSDTAR" xf "$TARBALL" \
    --strip-components=1 \
    -C "$SCRATCH" \
    "$strip_prefix/lib/$TRIPLE/libc++.a" \
    "$strip_prefix/lib/$TRIPLE/libc++abi.a" \
    "$strip_prefix/lib/$TRIPLE/libunwind.a" \
    "$strip_prefix/include/$TRIPLE/c++/v1/__config_site" \
    "$compiler_rt_member"

require_file() {
    local path="$1"
    if [ ! -f "$path" ]; then
        echo "ERROR: expected extracted file missing: $path" >&2
        exit 1
    fi
}

compiler_rt_rel="${compiler_rt_member#"$strip_prefix"/}"
require_file "$SCRATCH/lib/$TRIPLE/libc++.a"
require_file "$SCRATCH/lib/$TRIPLE/libc++abi.a"
require_file "$SCRATCH/lib/$TRIPLE/libunwind.a"
require_file "$SCRATCH/include/$TRIPLE/c++/v1/__config_site"
require_file "$SCRATCH/$compiler_rt_rel"

mkdir -p "$(dirname "$OUT_LIBCXX")" "$(dirname "$OUT_LIBCXXABI")" "$(dirname "$OUT_LIBUNWIND")" \
    "$(dirname "$OUT_COMPILER_RT")" "$(dirname "$OUT_CONFIG_SITE")"
cp "$SCRATCH/lib/$TRIPLE/libc++.a" "$OUT_LIBCXX"
cp "$SCRATCH/lib/$TRIPLE/libc++abi.a" "$OUT_LIBCXXABI"
cp "$SCRATCH/lib/$TRIPLE/libunwind.a" "$OUT_LIBUNWIND"
cp "$SCRATCH/$compiler_rt_rel" "$OUT_COMPILER_RT"
cp "$SCRATCH/include/$TRIPLE/c++/v1/__config_site" "$OUT_CONFIG_SITE"
"""

def _llvm_major_from_strip_prefix(strip_prefix):
    # strip_prefix is expected to look like LLVM-22.1.8-Linux-X64[/]
    version = strip_prefix.rstrip("/").split("-")[1]
    return version.split(".")[0]

def _llvm_prebuilt_extract_libcxx_impl(ctx):
    bsdtar = ctx.toolchains[_TAR_TOOLCHAIN_TYPE]
    tarball = ctx.file.tarball
    strip_prefix = ctx.attr.strip_prefix
    triple = "%s-unknown-linux-gnu" % ctx.attr.arch
    llvm_major = _llvm_major_from_strip_prefix(strip_prefix)

    out_libcxx = ctx.actions.declare_file("lib/%s/libc++.a" % triple)
    out_libcxxabi = ctx.actions.declare_file("lib/%s/libc++abi.a" % triple)
    out_libunwind = ctx.actions.declare_file("lib/%s/libunwind.a" % triple)
    out_compiler_rt = ctx.actions.declare_file("lib/clang/%s/lib/%s/libclang_rt.builtins.a" % (llvm_major, triple))
    out_config_site = ctx.actions.declare_file("include/%s/c++/v1/__config_site" % triple)

    ctx.actions.run_shell(
        inputs = [tarball],
        tools = [bsdtar.tarinfo.binary],
        outputs = [out_libcxx, out_libcxxabi, out_libunwind, out_compiler_rt, out_config_site],
        env = bsdtar.tarinfo.default_env,
        command = _LLVM_PREBUILT_EXTRACT_SCRIPT,
        arguments = [
            bsdtar.tarinfo.binary.path,
            tarball.path,
            strip_prefix,
            triple,
            out_libcxx.path,
            out_libcxxabi.path,
            out_libunwind.path,
            out_compiler_rt.path,
            out_config_site.path,
        ],
        mnemonic = "LlvmPrebuiltExtractLibcxx",
        progress_message = "Extracting libcxx files from LLVM prebuilt tarball for " + ctx.attr.arch,
    )

    return [
        DefaultInfo(files = depset([out_libcxx, out_libcxxabi, out_libunwind, out_compiler_rt, out_config_site])),
        OutputGroupInfo(
            libcxx = depset([out_libcxx, out_libcxxabi, out_libunwind]),
            compiler_rt = depset([out_compiler_rt]),
            config_site = depset([out_config_site]),
        ),
    ]

llvm_prebuilt_extract_libcxx = rule(
    implementation = _llvm_prebuilt_extract_libcxx_impl,
    attrs = {
        "tarball": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "The upstream LLVM tarball blob.",
        ),
        "strip_prefix": attr.string(
            mandatory = True,
            doc = "Archive strip prefix (e.g. LLVM-22.1.8-Linux-X64/).",
        ),
        "arch": attr.string(
            mandatory = True,
            values = ["aarch64", "x86_64"],
            doc = "Target architecture used to compute the GNU triple.",
        ),
    },
    toolchains = [_TAR_TOOLCHAIN_TYPE],
    doc = "Extracts libcxx, compiler_rt builtins, and __config_site from an LLVM tarball blob.",
)
