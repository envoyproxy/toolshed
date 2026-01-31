"""Macro for building fat runtime variants of hyperscan."""

load("@rules_cc//cc:defs.bzl", "cc_import", "cc_library")
load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cc_toolchain", "use_cc_toolchain")
load("@rules_cc//cc:action_names.bzl", "ACTION_NAMES")

def hs_exec_variant(name, arch, march_flag):
    """Build an architecture-specific variant of the runtime library.
    
    Args:
        name: Name of the variant (e.g., "core2", "avx2")
        arch: Architecture identifier for symbol prefixing
        march_flag: GCC -march flag (e.g., "-march=core2")
    """
    lib_name = "hs_exec_" + name
    renamed_name = lib_name + "_renamed"
    
    # Compile the runtime sources with specific architecture flags
    cc_library(
        name = lib_name,
        srcs = native.glob(
            [
                "src/crc32.c",
                "src/database.c",
                "src/runtime.c",
                "src/stream_compress.c",
                "src/hs_version.c",
                "src/hs_valid_platform.c",
                "src/fdr/*.c",
                "src/hwlm/*.c",
                "src/nfa/*.c",
                "src/rose/*.c",
                "src/som/*.c",
                "src/util/masked_move.c",
                "src/util/simd_utils.c",
                "src/util/state_compress.c",
            ],
            exclude = [
                "src/**/*_dump*.c",
                "src/**/test_*.c",
                "src/hwlm/noodle_engine_avx2.c",
                "src/hwlm/noodle_engine_avx512.c",
                "src/hwlm/noodle_engine_sse.c",
            ],
        ),
        hdrs = native.glob(["src/**/*.h"]),
        textual_hdrs = [
            "src/hwlm/noodle_engine_avx2.c",
            "src/hwlm/noodle_engine_avx512.c",
            "src/hwlm/noodle_engine_sse.c",
        ],
        copts = [
            "-std=c99",
            "-O3",
            "-DNDEBUG",
            "-fno-strict-aliasing",
            march_flag,
            "-Wno-unused-parameter",
            "-Wno-sign-compare",
        ],
        includes = [
            ".",
            "src",
        ],
        linkstatic = True,
        target_compatible_with = [
            "@platforms//cpu:x86_64",
            "@platforms//os:linux",
        ],
        visibility = ["//visibility:private"],
        deps = [":hs_common"],
    )
    
    # Rename symbols using the hermetic toolchain-based rule
    hs_rename_symbols(
        name = renamed_name,
        archive = ":" + lib_name,
        prefix = arch,
        target_compatible_with = [
            "@platforms//cpu:x86_64",
            "@platforms//os:linux",
        ],
    )
    
    # Import the renamed archive back as a cc_library
    cc_import(
        name = renamed_name + "_import",
        static_library = ":" + renamed_name,
        target_compatible_with = [
            "@platforms//cpu:x86_64",
            "@platforms//os:linux",
        ],
        visibility = ["//visibility:private"],
    )

# Keep symbols - from upstream keep.syms.in plus common libc symbols
KEEP_SYMBOLS = """hs_misc_alloc
hs_misc_free
hs_free_scratch
hs_stream_alloc
hs_stream_free
hs_scratch_alloc
hs_scratch_free
hs_database_alloc
hs_database_free
^_
^malloc$
^free$
^calloc$
^realloc$
^memcpy$
^memmove$
^memset$
^memcmp$
^strlen$
^strcmp$
^strncmp$
^strcpy$
^strncpy$
^printf$
^fprintf$
^sprintf$
^snprintf$
^abort$
^exit$
^pthread_
"""

def _hs_rename_symbols_impl(ctx):
    """Implementation for hs_rename_symbols rule.
    
    This rule extracts object files from a static archive, renames their symbols
    with a specified prefix (except for symbols in the keep list), and creates a
    new archive with the renamed symbols.
    """
    cc_toolchain = find_cc_toolchain(ctx)
    feature_configuration = cc_common.configure_features(
        ctx = ctx,
        cc_toolchain = cc_toolchain,
        requested_features = ctx.features,
        unsupported_features = ctx.disabled_features,
    )
    
    # Get tool path for the archiver
    ar_executable = cc_common.get_tool_for_action(
        feature_configuration = feature_configuration,
        action_name = ACTION_NAMES.cpp_link_static_library,
    )
    
    # Extract the static library from the cc_library's CcInfo provider
    input_archive = None
    if CcInfo in ctx.attr.archive:
        for linker_input in ctx.attr.archive[CcInfo].linking_context.linker_inputs.to_list():
            for lib in linker_input.libraries:
                if lib.static_library:
                    input_archive = lib.static_library
                    break
            if input_archive:
                break
    
    if not input_archive:
        fail("Could not find static library in archive attribute")
    
    output_archive = ctx.actions.declare_file(ctx.label.name + ".a")
    keep_syms = ctx.actions.declare_file(ctx.label.name + "_keep.syms")
    
    # Write the keep symbols file
    ctx.actions.write(
        output = keep_syms,
        content = KEEP_SYMBOLS,
    )
    
    # Create a script that performs the symbol renaming
    # The script accepts tool paths as arguments for flexibility in remote execution
    script = ctx.actions.declare_file(ctx.label.name + "_rename.sh")
    script_content = """#!/bin/bash
set -e

# Arguments: AR_PATH NM_PATH OBJCOPY_PATH PREFIX INPUT_AR OUTPUT_AR KEEPSYMS
# Convert all paths to absolute before cd, so they work from any directory
AR="$(realpath "$1")"
NM="$(realpath "$2")"
OBJCOPY="$(realpath "$3")"
PREFIX="$4"
INPUT_AR="$(realpath "$5")"
OUTPUT_AR="$(realpath "$6")"
KEEPSYMS="$(realpath "$7")"

# Create temporary directory for work
TMPDIR=$(mktemp -d)
trap "rm -rf ${TMPDIR}" EXIT

# Extract archive to temporary directory
cd "${TMPDIR}"
"${AR}" x "${INPUT_AR}"

# Process each object file
for obj in *.o; do
    [ -f "${obj}" ] || continue
    SYMSFILE="${obj}.syms"
    
    # Get all global symbols from the object, filter out keep symbols,
    # and create rename map
    # llvm-nm --format=posix outputs: symbol_name type address [size]
    # We extract only the symbol name (first field) and create the rename map
    "${NM}" --format=posix -g "${obj}" | awk '{print $1}' | grep -v -f "${KEEPSYMS}" | awk -v prefix="${PREFIX}" '{print $1 " " prefix "_" $1}' > "${SYMSFILE}" || true
    
    # Rename symbols if any need renaming
    if [ -s "${SYMSFILE}" ]; then
        "${OBJCOPY}" --redefine-syms="${SYMSFILE}" "${obj}"
    fi
    
    rm -f "${SYMSFILE}"
done

# Create output archive with renamed symbols
"${AR}" rcs "${OUTPUT_AR}" *.o

# Return to original directory
cd - > /dev/null
"""
    
    ctx.actions.write(
        output = script,
        content = script_content,
        is_executable = True,
    )
    
    # For LLVM toolchain, derive nm and objcopy paths from ar executable
    # The ar_executable is a string path, we need to construct nm and objcopy paths
    ar_dir = ar_executable.rpartition("/")[0]
    if ar_dir:
        nm_executable = ar_dir + "/llvm-nm"
        objcopy_executable = ar_dir + "/llvm-objcopy"
    else:
        # Fallback to PATH
        nm_executable = "llvm-nm"
        objcopy_executable = "llvm-objcopy"
    
    # Create args for the script
    args = ctx.actions.args()
    args.add(ar_executable)
    args.add(nm_executable)
    args.add(objcopy_executable)
    args.add(ctx.attr.prefix)
    args.add(input_archive)
    args.add(output_archive)
    args.add(keep_syms)
    
    # Run the script
    ctx.actions.run(
        inputs = depset(
            direct = [input_archive, keep_syms],
            transitive = [cc_toolchain.all_files],
        ),
        outputs = [output_archive],
        executable = script,
        arguments = [args],
        mnemonic = "RenameSymbols",
        progress_message = "Renaming symbols in %s with prefix %s" % (input_archive.short_path, ctx.attr.prefix),
        use_default_shell_env = True,
    )
    
    return [
        DefaultInfo(files = depset([output_archive])),
    ]

hs_rename_symbols = rule(
    implementation = _hs_rename_symbols_impl,
    attrs = {
        "archive": attr.label(
            mandatory = True,
            providers = [CcInfo],
            doc = "Input cc_library to extract static archive from and rename symbols in",
        ),
        "prefix": attr.string(
            mandatory = True,
            doc = "Prefix to add to renamed symbols",
        ),
        "_cc_toolchain": attr.label(
            default = "@bazel_tools//tools/cpp:current_cc_toolchain",
        ),
    },
    toolchains = use_cc_toolchain(),
    fragments = ["cpp"],
    doc = "Renames symbols in a static archive with a prefix, preserving allocation hooks and libc symbols",
)

