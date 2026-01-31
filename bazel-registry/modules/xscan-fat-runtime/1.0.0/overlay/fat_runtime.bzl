"""Fat runtime infrastructure for xscan (hyperscan/vectorscan) libraries.

This module provides symbol renaming and variant building infrastructure for creating
fat runtime builds of xscan libraries that support multiple CPU architectures.
"""

load("@rules_cc//cc:defs.bzl", "cc_import", "cc_library")
load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cc_toolchain", "use_cc_toolchain")
load("@bazel_tools//tools/cpp:toolchain_utils.bzl", "use_cpp_toolchain")

# Symbol patterns to keep (not rename with architecture prefix)
XSCAN_KEEP_SYMBOLS = [
    # Hyperscan/vectorscan allocation hooks
    "^hs_misc_alloc$",
    "^hs_misc_free$",
    "^hs_database_alloc$",
    "^hs_database_free$",
    "^hs_scratch_alloc$",
    "^hs_scratch_free$",
    "^hs_stream_alloc$",
    "^hs_stream_free$",
    "^hs_free_scratch$",
    
    # Cross-library symbols
    "^mmbit_",
    
    # System/libc symbols (underscore-prefixed are compiler internals)
    "^_",
    
    # Standard C library functions
    "^malloc$",
    "^free$",
    "^calloc$",
    "^realloc$",
    "^memcpy$",
    "^memmove$",
    "^memset$",
    "^memcmp$",
    "^strlen$",
    "^strcmp$",
    "^strncmp$",
    "^strcpy$",
    "^strncpy$",
    "^printf$",
    "^fprintf$",
    "^sprintf$",
    "^snprintf$",
    "^abort$",
    "^exit$",
    "^pthread_",
]

def _rename_symbols_impl(ctx):
    """Implementation of rename_symbols rule.
    
    Extracts objects from a static library, renames symbols with an architecture prefix
    (excluding symbols in the keep list), and recreates the archive.
    
    Args:
        ctx: Rule context
        
    Returns:
        DefaultInfo provider with the renamed archive
    """
    cc_toolchain = find_cc_toolchain(ctx)
    
    # Get the ar tool from the toolchain
    ar = cc_common.get_tool_for_action(
        feature_configuration = cc_common.configure_features(
            ctx = ctx,
            cc_toolchain = cc_toolchain,
            requested_features = ctx.features,
            unsupported_features = ctx.disabled_features,
        ),
        action_name = "@rules_cc//cc/toolchains/actions:cpp_link_static_library",
    )
    
    # Derive nm and objcopy from ar path (support LLVM toolchain layout)
    # ar is typically at <toolchain>/bin/llvm-ar or <toolchain>/bin/ar
    ar_dir = ar[:ar.rfind("/")]
    
    # Try to find llvm-nm first, then nm
    nm = ar_dir + "/llvm-nm"
    objcopy = ar_dir + "/llvm-objcopy"
    if "llvm-ar" not in ar:
        # Not an LLVM toolchain, use standard names
        nm = ar_dir + "/nm"
        objcopy = ar_dir + "/objcopy"
    
    input_archive = ctx.file.archive
    output_archive = ctx.outputs.out
    prefix = ctx.attr.prefix
    keep_symbols = ctx.attr.keep_symbols
    
    # Create a script to rename symbols
    script = ctx.actions.declare_file(ctx.label.name + "_rename.sh")
    
    script_content = """#!/bin/bash
set -e

AR="{ar}"
NM="{nm}"
OBJCOPY="{objcopy}"
INPUT="{input}"
OUTPUT="{output}"
PREFIX="{prefix}"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Extract all objects from the archive
cd $TMPDIR
$AR x "$INPUT"

# For each object file, rename symbols
for obj in *.o; do
    # Get all defined symbols (not undefined, not weak)
    $NM --defined-only --extern-only --format=posix "$obj" | awk '{{print $1}}' > symbols.txt
    
    # Generate objcopy rename commands
    rm -f redefine.txt
    while read -r symbol; do
        # Check if symbol should be kept (matches any keep pattern)
        keep=0
{keep_checks}
        
        if [ $keep -eq 0 ]; then
            echo "$symbol ${{PREFIX}}$symbol" >> redefine.txt
        fi
    done < symbols.txt
    
    # Apply renamings if any
    if [ -s redefine.txt ]; then
        $OBJCOPY --redefine-syms=redefine.txt "$obj" "$obj.new"
        mv "$obj.new" "$obj"
    fi
done

# Create new archive with renamed objects
$AR rcs "$OUTPUT" *.o
"""
    
    # Generate keep symbol checks
    keep_checks = ""
    for pattern in keep_symbols:
        # Convert pattern to grep-compatible regex
        # Pattern is already in grep extended regex format
        keep_checks += '        if echo "$symbol" | grep -qE \'{pattern}\'; then keep=1; fi\n'.format(
            pattern = pattern,
        )
    
    ctx.actions.write(
        output = script,
        content = script_content.format(
            ar = ar,
            nm = nm,
            objcopy = objcopy,
            input = input_archive.path,
            output = output_archive.path,
            prefix = prefix,
            keep_checks = keep_checks,
        ),
        is_executable = True,
    )
    
    ctx.actions.run(
        inputs = [input_archive] + cc_toolchain.all_files.to_list(),
        outputs = [output_archive],
        executable = script,
        mnemonic = "RenameSymbols",
        progress_message = "Renaming symbols in %s with prefix %s" % (input_archive.short_path, prefix),
        use_default_shell_env = True,
    )
    
    return [DefaultInfo(files = depset([output_archive]))]

rename_symbols = rule(
    implementation = _rename_symbols_impl,
    attrs = {
        "archive": attr.label(
            mandatory = True,
            allow_single_file = [".a"],
            doc = "The static library archive to process",
        ),
        "prefix": attr.string(
            mandatory = True,
            doc = "Prefix to add to renamed symbols",
        ),
        "keep_symbols": attr.string_list(
            default = XSCAN_KEEP_SYMBOLS,
            doc = "List of symbol patterns (grep extended regex) to keep unchanged",
        ),
        "out": attr.output(
            mandatory = True,
            doc = "Output archive with renamed symbols",
        ),
        "_cc_toolchain": attr.label(
            default = Label("@bazel_tools//tools/cpp:current_cc_toolchain"),
        ),
    },
    toolchains = use_cc_toolchain(),
    fragments = ["cpp"],
    doc = """Rename symbols in a static library with an architecture prefix.
    
    This rule extracts object files from a static library, renames symbols
    (except those matching keep patterns), and recreates the archive.
    """,
)

def exec_variant(
        name,
        arch,
        march_flag,
        common_lib,
        srcs,
        hdrs,
        copts = [],
        includes = [],
        target_constraints = [],
        extra_keep_symbols = []):
    """Create an execution variant for a specific CPU architecture.
    
    This macro creates:
    1. A cc_library compiled for the specific architecture
    2. A rename_symbols target that prefixes symbols with the architecture name
    3. A cc_import for the renamed static library
    4. A final cc_library that exports the renamed variant
    
    Args:
        name: Base name for the variant targets
        arch: Architecture identifier (e.g., "avx2", "sse42", "core")
        march_flag: Compiler march flag (e.g., "-march=core-avx2")
        common_lib: Label of the common library dependency
        srcs: Source files for this variant
        hdrs: Header files for this variant
        copts: Additional compiler options
        includes: Include directories
        target_constraints: Platform constraints for this variant
        extra_keep_symbols: Additional symbols to keep (not rename)
    """
    
    # Internal library with arch-specific compilation
    internal_lib = name + "_" + arch + "_internal"
    cc_library(
        name = internal_lib,
        srcs = srcs,
        hdrs = hdrs,
        copts = copts + [march_flag],
        includes = includes,
        target_compatible_with = target_constraints,
        linkstatic = True,
        deps = [common_lib],
        visibility = ["//visibility:private"],
    )
    
    # Renamed archive
    renamed_archive = name + "_" + arch + "_renamed.a"
    rename_symbols(
        name = name + "_" + arch + "_rename",
        archive = internal_lib,
        prefix = arch + "_",
        keep_symbols = XSCAN_KEEP_SYMBOLS + extra_keep_symbols,
        out = renamed_archive,
        target_compatible_with = target_constraints,
    )
    
    # Import the renamed archive
    import_name = name + "_" + arch + "_import"
    cc_import(
        name = import_name,
        static_library = renamed_archive,
        target_compatible_with = target_constraints,
        visibility = ["//visibility:private"],
    )
    
    # Final exported library
    cc_library(
        name = name + "_" + arch,
        target_compatible_with = target_constraints,
        visibility = ["//visibility:public"],
        deps = [
            import_name,
            common_lib,
        ],
    )
