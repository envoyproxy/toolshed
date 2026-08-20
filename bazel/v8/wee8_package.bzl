"""Starlark rules for building and packaging the V8 wee8 prebuilt static library.

Provides:
  wee8_fat_archive  — rule that creates a fat libwee8.a from @v8//:wee8 and its
                      transitive PIC static deps (excluding abseil/icu), using
                      the archiver from the resolved C++ toolchain.
  wee8_headers      — rule that maps @v8//:wee8 headers from their execroot
                      paths to their tarball paths, returning PackageFilesInfo.
  wee8_package      — macro that wires both into a pkg_tar per arch/stdlib.

Both rules carry the arch/stdlib transition; pkg_tar consumes their outputs in
the default configuration and needs none.
"""

load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load("@bazel_tools//tools/cpp:toolchain_utils.bzl", "find_cpp_toolchain", "use_cpp_toolchain")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
load("@rules_pkg//pkg:providers.bzl", "PackageFilesInfo")
load("//:versions.bzl", "V8_VERSION")
load(":wee8_prebuilt.bzl", "WEE8_DEFAULT_STDLIB", "WEE8_STDLIBS", "wee8_archive_filename")

_V8_VERSION = V8_VERSION

_ARCH_PLATFORMS = {
    ("x86_64", "libcxx"): "@toolchains_llvm//platforms:linux-x86_64",
    ("aarch64", "libcxx"): "@toolchains_llvm//platforms:linux-aarch64",
    ("x86_64", "libstdcxx"): "//platforms:linux_x86_64_libstdcxx",
    # This does not currently work as it would require x-libs similar to how we provision llvm
    # ("aarch64", "libstdcxx"): "//platforms:linux_aarch64_libstdcxx",
}

# The transition sets the target platform only. Execution platforms are supplied
# by config, not here:
#
#   --config=gcc      registers //platforms:linux_x86_64_gcc_worker, which
#                     carries //compile:gcc_worker so the gcc toolchain resolves
#                     locally.
#   --config=rbe-gcc  overrides that with the //platforms/rbe gcc platforms,
#                     which also carry the `container-image` exec property that
#                     EngFlow matches on.
#
# Setting --extra_execution_platforms from the transition would clobber the RBE
# platforms, and dispatched actions would fail with `No matching action runner
# found` because the injected platform has no exec properties.

def _wee8_transition_impl(settings, attr):
    return {
        "//command_line_option:platforms": [
            _ARCH_PLATFORMS[(attr.arch, attr.stdlib)],
        ],
    }

_wee8_transition = transition(
    implementation = _wee8_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:platforms"],
)

_TRANSITION_ATTRS = {
    "wee8": attr.label(
        mandatory = True,
        providers = [CcInfo],
        doc = "The @v8//:wee8 cc_library target.",
        cfg = _wee8_transition,
    ),
    "arch": attr.string(
        mandatory = True,
        values = ["x86_64", "aarch64"],
        doc = "Target architecture.",
    ),
    "stdlib": attr.string(
        default = WEE8_DEFAULT_STDLIB,
        values = WEE8_STDLIBS,
        doc = "Standard library ABI flavour.",
    ),
    "_allowlist_function_transition": attr.label(
        default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
    ),
}

# ── Fat archive ──────────────────────────────────────────────────────────────

# argv[1]  archiver executable (from the resolved cc toolchain)
# argv[2]  output libwee8.a path
# argv[3]  params file listing one execroot-relative object path per line
#
# We archive the object files DIRECTLY rather than extracting the deps' `.a`/`.lo`
# archives and re-archiving. V8 emits many objects that share a basename (e.g. two
# `heap.pic.o`, two `factory.pic.o`, two `allocation.pic.o`, from same-named
# sources in different directories). Archive members are stored by basename, so
# extracting to the filesystem (`ar x`) makes the second `heap.pic.o` clobber the
# first, silently dropping one object of each colliding pair and every symbol it
# defined (Factory::NewSymbol, Heap::CollectAllGarbage, VirtualMemory::~…, PrintF,
# …). The distinct object Files have distinct on-disk paths, so archiving them
# straight into libwee8.a keeps both. The result carries duplicate member
# basenames, exactly like V8's own `.lo`, which links correctly because the linker
# reads members by content, not by filesystem name. `@file` avoids ARG_MAX with
# ~1200 objects; both llvm-ar and GNU ar expand it.
_ARCHIVE_SCRIPT = r"""
set -e -o pipefail

AR="$PWD/$1"
OUT="$2"
PARAMS="$3"

if [ ! -s "$PARAMS" ]; then
    echo "ERROR: no object files to archive (empty params file)" >&2
    exit 1
fi

"$AR" Drcs "$OUT" "@$PARAMS"
"""

def _wee8_fat_archive_impl(ctx):
    # `wee8` carries a transition, so the dep is a list of configured targets.
    # The transition always yields exactly one configuration, hence index 0.
    cc_info = ctx.attr.wee8[0][CcInfo]
    excluded = ctx.attr.exclude_lib_prefixes

    # Collect the actual object files from transitive linker inputs.
    #
    # `exclude_lib_prefixes` is matched against each OBJECT's path. Under bzlmod
    # an object lives at .../external/<canonical_repo>/<pkg>/_objs/.../foo.pic.o,
    # so the defaults ("abseil-cpp+", "icu+") are the canonical repo directory
    # components — they match every abseil/icu object, not just an archive name.
    # (Verified: all abseil objects contain "abseil-cpp+"; the noicu build pulls
    # in zero icu objects.) abseil/icu are excluded because consumers link their
    # own; bundling them would bloat libwee8.a and risk ODR/duplicate symbols.
    #
    # pic_objects and objects are the SAME translation units compiled two ways,
    # not a partition, so taking one list is correct (both would double every
    # object). We prefer PIC to match the prebuilt's PIC ABI; fall back to
    # non-PIC only when a lib was built without PIC.
    #
    # Dedup by path (an object may appear in several linker inputs).
    seen = {}
    objects = []
    for li in cc_info.linking_context.linker_inputs.to_list():
        for lib in li.libraries:
            objs = lib.pic_objects if lib.pic_objects else lib.objects
            if not objs:
                # A dep exposing only a prebuilt archive with no object list.
                # None of @v8//:wee8's current deps hit this; fail loudly rather
                # than silently drop it if a future V8 bump introduces one.
                f = lib.pic_static_library or lib.static_library
                if f and not any([ex in f.path for ex in excluded]):
                    fail(
                        "wee8_fat_archive: library {} exposes an archive but no ".format(f.path) +
                        "object list; extend the rule to extract it uniquely.",
                    )
                continue
            for o in objs:
                if o.path in seen or any([ex in o.path for ex in excluded]):
                    continue
                seen[o.path] = True
                objects.append(o)

    if not objects:
        fail(
            "wee8_fat_archive: no object files found in @v8//:wee8 deps. " +
            "Verify that @v8//:wee8 is a cc_library exposing [pic_]objects.",
        )

    cc_toolchain = find_cpp_toolchain(ctx)
    feature_configuration = cc_common.configure_features(
        ctx = ctx,
        cc_toolchain = cc_toolchain,
        requested_features = ctx.features,
        unsupported_features = ctx.disabled_features,
    )
    ar = cc_common.get_tool_for_action(
        feature_configuration = feature_configuration,
        action_name = ACTION_NAMES.cpp_link_static_library,
    )

    params = ctx.actions.declare_file("%s/libwee8.objects.params" % ctx.label.name)
    # Trailing newline: llvm-ar and GNU ar both tolerate its absence, but it is
    # free insurance against an archiver that expects newline-terminated entries.
    ctx.actions.write(params, "\n".join([o.path for o in objects]) + "\n")

    out = ctx.actions.declare_file("%s/lib/libwee8.a" % ctx.label.name)
    ctx.actions.run_shell(
        inputs = depset(objects + [params], transitive = [cc_toolchain.all_files]),
        outputs = [out],
        command = _ARCHIVE_SCRIPT,
        arguments = [ar, out.path, params.path],
        mnemonic = "V8WeeEightArchive",
        progress_message = "Creating fat libwee8.a (%d objects) for linux-%s (%s)" % (
            len(objects),
            ctx.attr.arch,
            ctx.attr.stdlib,
        ),
    )

    return [
        DefaultInfo(files = depset([out])),
        PackageFilesInfo(
            dest_src_map = {"lib/libwee8.a": out},
            attributes = {},
        ),
    ]

wee8_fat_archive = rule(
    implementation = _wee8_fat_archive_impl,
    attrs = _TRANSITION_ATTRS | {
        "exclude_lib_prefixes": attr.string_list(
            default = ["abseil-cpp+", "icu+"],
            doc = "Objects whose path contains any of these substrings are " +
                  "excluded. Defaults are the canonical bzlmod repo directory " +
                  "components for abseil/icu (which appear in every object path " +
                  "under those repos), so consumers supply their own abseil/icu.",
        ),
        "_cc_toolchain": attr.label(
            default = "@bazel_tools//tools/cpp:current_cc_toolchain",
        ),
    },
    fragments = ["cpp"],
    toolchains = use_cpp_toolchain(),
    doc = "Merges @v8//:wee8 and its static deps into a single libwee8.a. " +
          "The archive INTENTIONALLY contains members with duplicate basenames " +
          "(V8 emits same-named objects from different dirs); this is required " +
          "for correctness and matches V8's own .lo. Do not 'dedup' by basename " +
          "or extract-and-rearchive (`ar x`) — that clobbers members and drops " +
          "symbols. `ar t` on the output is therefore ambiguous by design.",
)

# ── Headers ──────────────────────────────────────────────────────────────────

def _wee8_headers_impl(ctx):
    cc_info = ctx.attr.wee8[0][CcInfo]

    # Only the v8+ module's own headers, source and generated.
    headers = [
        f
        for f in cc_info.compilation_context.headers.to_list()
        if "/v8+/" in f.path
    ]

    # In the execroot, @v8 source files live at external/v8+/<rel> and
    # generated files at bazel-out/<cfg>/bin/external/v8+/<rel>. Both map to
    # <rel> in the tarball.
    dest_src_map = {}
    for f in headers:
        idx = f.path.find("external/v8+/")
        if idx == -1:
            continue
        rel = f.path[idx + len("external/v8+/"):]
        dest_src_map[rel] = f

        # wasm-api headers are also needed at include/ for '#include "wasm.h"'
        if rel.endswith("wasm-api/wasm.h"):
            dest_src_map["include/wasm.h"] = f

    if not dest_src_map:
        fail("wee8_headers: no headers found in @v8//:wee8 CcInfo.")

    return [
        DefaultInfo(files = depset(headers)),
        PackageFilesInfo(
            dest_src_map = dest_src_map,
            attributes = {},
        ),
    ]

wee8_headers = rule(
    implementation = _wee8_headers_impl,
    attrs = _TRANSITION_ATTRS,
    doc = "Maps @v8//:wee8 headers from execroot paths to tarball paths.",
)

# ── Public macro ─────────────────────────────────────────────────────────────

def wee8_package_target_name(arch, stdlib = WEE8_DEFAULT_STDLIB):
    return "wee8_package_linux_%s_%s" % (arch, stdlib)

def wee8_package(name = None, arch = None, stdlib = WEE8_DEFAULT_STDLIB, version = _V8_VERSION):
    """Creates a packaging target for the given arch and stdlib.

    libcxx preserves the historical unsuffixed artifact name for compatibility.
    libstdcxx uses the explicit -libstdcxx suffix.

    Tarball layout:
      lib/libwee8.a        fat static archive (V8 + fast_float/simdutf/highway/fp16)
      include/             V8 public C++ API headers + wasm-api headers
      third_party/         canonical third_party/wasm-api/ paths
      src/                 internal V8 headers exported via CcInfo (e.g. src/wasm/c-api.h)
    """
    name = name or wee8_package_target_name(arch, stdlib)

    wee8_fat_archive(
        name = "%s_archive" % name,
        wee8 = "@v8//:wee8",
        arch = arch,
        stdlib = stdlib,
        tags = ["manual"],
        target_compatible_with = ["@platforms//os:linux"],
    )

    wee8_headers(
        name = "%s_headers" % name,
        wee8 = "@v8//:wee8",
        arch = arch,
        stdlib = stdlib,
        tags = ["manual"],
        target_compatible_with = ["@platforms//os:linux"],
    )

    pkg_tar(
        name = name,
        srcs = [
            ":%s_archive" % name,
            ":%s_headers" % name,
        ],
        compression_level = -1,
        extension = "tar.xz",
        owner = "0.0",
        ownername = ".",
        package_file_name = wee8_archive_filename(version, arch, stdlib),
        portable_mtime = True,
        stamp = 0,
        tags = ["manual"],
        target_compatible_with = ["@platforms//os:linux"],
    )
