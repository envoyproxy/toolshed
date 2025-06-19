"""Autotools toolchain definition."""

AutotoolsInfo = provider(
    doc = "Information about an autotools installation",
    fields = {
        "m4": "Path to m4 binary",
        "m4_file": "File reference to m4 binary",
        "autoconf": "Path to autoconf binary",
        "autoconf_file": "File reference to autoconf binary",
        "autoheader": "Path to autoheader binary",
        "autoheader_file": "File reference to autoheader binary",
        "autoreconf": "Path to autoreconf binary",
        "autoreconf_file": "File reference to autoreconf binary",
        "automake": "Path to automake binary",
        "automake_file": "File reference to automake binary",
        "aclocal": "Path to aclocal binary",
        "aclocal_file": "File reference to aclocal binary",
        "libtoolize": "Path to libtoolize binary",
        "libtoolize_file": "File reference to libtoolize binary",
        "libtool": "Path to libtool binary",
        "libtool_file": "File reference to libtool binary",
        "env": "Environment variables to set",
        "make_vars": "Make variables for foreign_cc",
        "data": "Additional data dependencies",
    },
)

def _autotools_toolchain_impl(ctx):
    """Implementation for autotools toolchain rule."""
    # Collect all file references
    files = {}
    paths = {}

    # Helper to process each tool
    def process_tool(name, label_attr, path_attr):
        file_ref = getattr(ctx.file, name, None) if hasattr(ctx.file, name) else None
        if file_ref:
            files[name + "_file"] = file_ref
            paths[name] = file_ref.path
        else:
            paths[name] = getattr(ctx.attr, path_attr, name)

    # Process all tools
    tools = [
        ("m4", "m4", "m4_path"),
        ("autoconf", "autoconf", "autoconf_path"),
        ("autoheader", "autoheader", "autoheader_path"),
        ("autoreconf", "autoreconf", "autoreconf_path"),
        ("automake", "automake", "automake_path"),
        ("aclocal", "aclocal", "aclocal_path"),
        ("libtoolize", "libtoolize", "libtoolize_path"),
        ("libtool", "libtool", "libtool_path"),
    ]

    for tool_name, label_name, path_name in tools:
        process_tool(tool_name, label_name, path_name)

    # Collect all data files including perl
    data_files = ctx.files.data + ctx.files.perl_runtime
    for name, file_ref in files.items():
        if file_ref:
            data_files = data_files + [file_ref]

    # Build make variables for foreign_cc
    make_vars = {
        "M4": "$EXT_BUILD_DEPS$/bin/m4",
        "AUTOCONF": "$EXT_BUILD_DEPS$/bin/autoconf",
        "AUTOHEADER": "$EXT_BUILD_DEPS$/bin/autoheader",
        "AUTORECONF": "$EXT_BUILD_DEPS$/bin/autoreconf",
        "AUTOMAKE": "$EXT_BUILD_DEPS$/bin/automake",
        "ACLOCAL": "$EXT_BUILD_DEPS$/bin/aclocal",
        "LIBTOOLIZE": "$EXT_BUILD_DEPS$/bin/libtoolize",
        "LIBTOOL": "$EXT_BUILD_DEPS$/bin/libtool",
        "AUTOM4TE": "$EXT_BUILD_DEPS$/bin/autom4te",
        "PERL": "$EXT_BUILD_DEPS$/bin/perl",
        "ACLOCAL_PATH": "$EXT_BUILD_DEPS$/share/aclocal:$EXT_BUILD_DEPS$/share/aclocal-1.17",
        "autom4te_perllibdir": "$EXT_BUILD_DEPS$/share/autoconf",
        "pkgauxdir": "$EXT_BUILD_DEPS$/share/libtool/build-aux",
        "pkgdatadir": "$EXT_BUILD_DEPS$/share/libtool",
    }

    # Merge with user env
    all_env = dict(make_vars)
    all_env.update(ctx.attr.env)

    # Build the info provider
    info_fields = {
        "env": all_env,
        "make_vars": make_vars,
        "data": data_files,
    }
    info_fields.update(paths)
    info_fields.update(files)

    return [
        platform_common.ToolchainInfo(
            autotools_info = AutotoolsInfo(**info_fields),
        ),
    ]

autotools_toolchain = rule(
    implementation = _autotools_toolchain_impl,
    attrs = {
        # M4
        "m4": attr.label(
            doc = "M4 executable file",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
        "m4_path": attr.string(
            doc = "Path to m4 executable (for preinstalled toolchain)",
        ),
        # Autoconf tools
        "autoconf": attr.label(
            doc = "Autoconf executable file",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
        "autoconf_path": attr.string(
            doc = "Path to autoconf executable (for preinstalled toolchain)",
        ),
        "autoheader": attr.label(
            doc = "Autoheader executable file",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
        "autoheader_path": attr.string(
            doc = "Path to autoheader executable (for preinstalled toolchain)",
        ),
        "autoreconf": attr.label(
            doc = "Autoreconf executable file",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
        "autoreconf_path": attr.string(
            doc = "Path to autoreconf executable (for preinstalled toolchain)",
        ),
        # Automake tools
        "automake": attr.label(
            doc = "Automake executable file",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
        "automake_path": attr.string(
            doc = "Path to automake executable (for preinstalled toolchain)",
        ),
        "aclocal": attr.label(
            doc = "Aclocal executable file",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
        "aclocal_path": attr.string(
            doc = "Path to aclocal executable (for preinstalled toolchain)",
        ),
        # Libtool
        "libtoolize": attr.label(
            doc = "Libtoolize executable file",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
        "libtoolize_path": attr.string(
            doc = "Path to libtoolize executable (for preinstalled toolchain)",
        ),
        "libtool": attr.label(
            doc = "Libtool executable file",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
        "libtool_path": attr.string(
            doc = "Path to libtool executable (for preinstalled toolchain)",
        ),
        "env": attr.string_dict(
            doc = "Environment variables to set when using autotools",
            default = {},
        ),
        "data": attr.label_list(
            doc = "Additional files needed by autotools",
            allow_files = True,
            cfg = "exec",
        ),
        "perl_runtime": attr.label_list(
            doc = "Perl runtime for autotools scripts",
            allow_files = True,
            cfg = "exec",
        ),
    },
    provides = [platform_common.ToolchainInfo],
)

def get_autotools_data(ctx):
    """Get autotools data from the toolchain.

    Args:
        ctx: The rule context

    Returns:
        A struct containing:
        - All tool paths
        - All tool file references
        - env: Environment variables
        - data: Data files
    """
    toolchain = ctx.toolchains["//toolchains/autotools:autotools_toolchain_type"]
    if not toolchain:
        fail("No autotools toolchain found. Did you register the toolchain?")

    info = toolchain.autotools_info
    return struct(
        m4 = info.m4,
        m4_file = info.m4_file,
        autoconf = info.autoconf,
        autoconf_file = info.autoconf_file,
        autoheader = info.autoheader,
        autoheader_file = info.autoheader_file,
        autoreconf = info.autoreconf,
        autoreconf_file = info.autoreconf_file,
        automake = info.automake,
        automake_file = info.automake_file,
        aclocal = info.aclocal,
        aclocal_file = info.aclocal_file,
        libtoolize = info.libtoolize,
        libtoolize_file = info.libtoolize_file,
        libtool = info.libtool,
        libtool_file = info.libtool_file,
        env = info.env,
        data = info.data,
    )
