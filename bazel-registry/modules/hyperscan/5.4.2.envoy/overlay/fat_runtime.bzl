"""Macro for building fat runtime variants of hyperscan."""

load("@rules_cc//cc:defs.bzl", "cc_import", "cc_library")

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
    
    # Extract the static library and rename symbols
    native.genrule(
        name = renamed_name,
        srcs = [":" + lib_name],
        outs = ["lib" + renamed_name + ".a"],
        cmd = """
            # Find the .a file in the inputs
            for f in $(SRCS); do
                if [[ "$$f" == *.a ]]; then
                    INPUT_AR="$$f"
                    break
                fi
            done
            if [ -z "$$INPUT_AR" ]; then
                echo "Error: Could not find .a file in inputs"
                exit 1
            fi
            # Run the symbol renaming script
            $(location :rename_symbols.sh) """ + arch + """ "$$INPUT_AR" $@
        """,
        tools = [":rename_symbols.sh"],
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

