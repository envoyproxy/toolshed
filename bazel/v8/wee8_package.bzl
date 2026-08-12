"""Starlark rules for building and packaging the V8 wee8 prebuilt static library.

Provides:
  wee8_fat_archive — rule that creates a fat libwee8.a from @v8//:wee8 and
                     its transitive PIC static deps (excluding abseil/icu).
  wee8_package     — macro that creates per-arch packaging rules producing
                     v8-wee8-<version>-linux-<arch>.tar.xz.
"""

load("//:versions.bzl", "V8_VERSION")

_V8_VERSION = V8_VERSION

# Shell script run as a single Bazel action:
#   argv[1]       output tarball path
#   argv[2]       arch string (x86_64 | aarch64)
#   argv[3..]     paths to PIC static libraries (from @v8//:wee8 CcInfo)
#   --headers
#   argv[N..]     paths to V8 header files (from @v8//:wee8 CcInfo, filtered)
#
# The action is no-remote-exec because `ar` must match the target toolchain
# and is not staged to RBE workers.  The resulting tarball IS remote-cacheable.
_PACKAGE_SCRIPT = r"""
set -e -o pipefail
OUT="$1"
ARCH="$2"
shift 2

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
STAGING="$TMPDIR/staging"
mkdir -p "$STAGING/lib" "$STAGING/include"

# ── Split argv into library list and header list at '--headers' sentinel ──

LIBS=()
HEADERS=()
mode=libs
for a in "$@"; do
    if [ "$a" = "--headers" ]; then
        mode=headers
    elif [ "$mode" = libs ]; then
        LIBS+=("$a")
    else
        HEADERS+=("$a")
    fi
done

# ── 1. Create fat libwee8.a ────────────────────────────────────────────────

OBJ_DIR="$TMPDIR/objs"
mkdir "$OBJ_DIR"
i=0
for lib in "${LIBS[@]}"; do
    i=$((i+1))
    subdir="$OBJ_DIR/$i"
    mkdir "$subdir"
    ar x --output="$subdir" "$lib" 2>/dev/null \
        || (cd "$subdir" && ar x "$lib" 2>/dev/null) \
        || true
done
n=0
while IFS= read -r obj; do
    n=$((n+1))
    cp "$obj" "$OBJ_DIR/o_${n}.o"
done < <(find "$OBJ_DIR" -mindepth 2 -name '*.o' | LC_ALL=C sort)
[ "$n" -gt 0 ] || { echo "ERROR: no .o files found in supplied static libraries" >&2; exit 1; }
ar rcs "$STAGING/lib/libwee8.a" "$OBJ_DIR"/o_*.o

# ── 2. Copy headers (preserve path relative to V8 repo root) ──────────────

# In the Bazel execroot, @v8 source files live at  external/v8+/<rel>
# and generated files at  bazel-out/<cfg>/bin/external/v8+/<rel>.
for f in "${HEADERS[@]}"; do
    rel="${f#external/v8+/}"
    if [ "$rel" = "$f" ]; then
        # generated file — strip bazel-out/<cfg>/bin/ prefix
        rel="${f#*/bin/external/v8+/}"
    fi
    [ "$rel" = "$f" ] && continue  # not a v8+ file, skip
    dst="$STAGING/$rel"
    mkdir -p "$(dirname "$dst")"
    cp "$f" "$dst"
    # wasm-api headers are also needed at include/ for '#include "wasm.h"'
    if echo "$f" | grep -q "wasm-api/wasm\.h"; then
        cp "$f" "$STAGING/include/$(basename "$f")"
    fi
done

# ── 3. Assemble tarball ────────────────────────────────────────────────────

tar_dirs=()
for d in lib include src third_party; do
    [ -d "$STAGING/$d" ] && tar_dirs+=("$d")
done
[ "${#tar_dirs[@]}" -gt 0 ] || { echo "ERROR: staging directory is empty" >&2; exit 1; }
tar -cJf "$OUT" -C "$STAGING" "${tar_dirs[@]}"
"""

# ── Rule implementation ─────────────────────────────────────────────────────

def _wee8_package_impl(ctx):
    cc_info = ctx.attr.wee8[CcInfo]
    excluded = ctx.attr.exclude_lib_prefixes

    # Collect PIC static libraries from transitive linker inputs.
    # abseil-cpp and icu are provided by consumers — exclude them.
    seen = {}
    pic_libs = []
    for li in cc_info.linking_context.linker_inputs.to_list():
        for lib in li.libraries:
            f = lib.pic_static_library or lib.static_library
            if not f or f.path in seen:
                continue
            seen[f.path] = True
            if any([ex in f.path for ex in excluded]):
                continue
            pic_libs.append(f)

    if not pic_libs:
        fail(
            "wee8_package: no static libraries found in @v8//:wee8 deps. " +
            "Verify that @v8//:wee8 is a cc_library with [pic_]static_library outputs.",
        )

    # Collect V8 headers from the CcInfo compilation context.
    # Filter to only the v8+ module's own files (source and generated).
    v8_headers = [
        f
        for f in cc_info.compilation_context.headers.to_list()
        if "/v8+/" in f.path
    ]

    out = ctx.actions.declare_file(
        "v8-wee8-%s-linux-%s.tar.xz" % (ctx.attr.version, ctx.attr.arch),
    )

    ctx.actions.run_shell(
        inputs = depset(pic_libs + v8_headers),
        outputs = [out],
        command = _PACKAGE_SCRIPT,
        arguments = (
            [out.path, ctx.attr.arch] +
            [f.path for f in pic_libs] +
            ["--headers"] +
            [f.path for f in v8_headers]
        ),
        mnemonic = "V8WeeEightPackage",
        progress_message = "Packaging V8 wee8 prebuilt for linux-%s" % ctx.attr.arch,
        # ar and tar must run on the local executor; the tarball is still
        # remote-cacheable once produced.
        execution_requirements = {"no-remote-exec": "1"},
    )
    return [DefaultInfo(files = depset([out]))]

_wee8_package = rule(
    implementation = _wee8_package_impl,
    attrs = {
        "wee8": attr.label(
            mandatory = True,
            providers = [CcInfo],
            doc = "The @v8//:wee8 cc_library target.",
        ),
        "arch": attr.string(
            mandatory = True,
            values = ["x86_64", "aarch64"],
            doc = "Target architecture string embedded in the output filename.",
        ),
        "version": attr.string(
            default = _V8_VERSION,
            doc = "V8 version string embedded in the output filename.",
        ),
        "exclude_lib_prefixes": attr.string_list(
            default = ["abseil-cpp+", "icu+"],
            doc = "Libs whose path contains any of these strings are excluded from the fat archive.",
        ),
    },
    doc = "Packages @v8//:wee8 as a prebuilt static library tarball for the given arch.",
)

# ── Public macro ────────────────────────────────────────────────────────────

def wee8_package(arch, version = _V8_VERSION):
    """Creates a packaging rule for the given arch.

    Produces:
      //v8:wee8_package_linux_<arch>  →  v8/v8-wee8-<version>-linux-<arch>.tar.xz

    Tarball layout:
      lib/libwee8.a        fat static archive (V8 + fast_float/simdutf/highway/fp16)
      include/             V8 public C++ API headers + wasm-api headers
      third_party/         canonical third_party/wasm-api/ paths
      src/                 internal V8 headers exported via CcInfo (e.g. src/wasm/c-api.h)
    """
    _wee8_package(
        name = "wee8_package_linux_%s" % arch,
        wee8 = "@v8//:wee8",
        arch = arch,
        version = version,
        tags = ["manual"],
    )
