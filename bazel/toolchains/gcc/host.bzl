"""Host GCC toolchain repository.

This replaces a hermetic toolchain only when a root module explicitly declares
`gcc.host(...)`: a hermetic toolchain never falls back to host tools, headers or
libraries. It is also the separate fallback toolchain (`@gcc_host`) for hosts that no
hermetic archive runs on.
"""

# The hermetic archives all run on x86_64 Linux, whatever they target.
_HERMETIC_HOST_ARCH = "x86_64"

# `os.arch` spellings of the architectures that a host GCC toolchain supports.
_ARCHES = {
    "aarch64": "aarch64",
    "amd64": "x86_64",
    "arm64": "aarch64",
    "x86_64": "x86_64",
}

# The `gcc -print-search-dirs` line naming the compiler's own directory.
_INSTALL = "install: "

def gcc_tool_names(tool, target, major):
    """Return the names a GCC-owned tool can be installed under, the plain one first.

    Installations with several GCC releases version the names, eg `gcov-14`.

    Args:
      tool: The tool, eg `gcc` or `gcov`.
      target: The compiler's target, eg `aarch64-linux-gnu`.
      major: The compiler's major version.

    Returns:
      A list of file names.
    """
    return [tool, tool + "-" + major, target + "-" + tool, target + "-" + tool + "-" + major]

def banner_major(banner):
    """Return the major version in a GCC tool's `--version` output, or None.

    The version follows the parenthesised vendor: `gcov (Debian 14.2.0-19) 14.2.0`,
    `gcov (GCC) 14.2.1 20240912 (Red Hat 14.2.1-3)`.

    Args:
      banner: The `--version` output.

    Returns:
      The major version as a string, or None if it cannot be parsed.
    """
    line = banner.split("\n")[0]
    _, separator, rest = line.partition(") ")
    words = (rest if separator else line).strip().split(" ")
    major = (words[0] if separator else words[-1]).split(".")[0]
    return major if major.isdigit() else None

def _execute(ctx, arguments):
    result = ctx.execute(arguments, environment = {"LC_ALL": "C"})
    if result.return_code != 0:
        fail("Host GCC command %r failed (exit code %s): %s" % (arguments, result.return_code, result.stderr))
    return result

def _detect_version(ctx, gcc, declared_version):
    banner = _execute(ctx, [gcc, "--version"]).stdout
    if "clang" in banner.lower():
        fail("Host GCC must be GCC, not clang: %s" % gcc)
    version = _execute(ctx, [gcc, "-dumpfullversion", "-dumpversion"]).stdout.strip()
    components = version.split(".")
    if not version or not all([component.isdigit() for component in components]):
        fail("Could not parse the installed GCC version: %r" % version)
    if declared_version and declared_version.split(".")[0] != components[0]:
        fail("gcc.host(gcc_version = %r) does not match the installed GCC version %s" % (declared_version, version))
    return version

def _builtin_include_directories(ctx, gxx):
    ctx.file("include_probe.cc", "")
    result = _execute(ctx, [gxx, "-E", "-x", "c++", str(ctx.path("include_probe.cc")), "-v"])
    directories = []
    in_search_list = False
    complete = False
    for line in result.stderr.split("\n"):
        line = line.strip()
        if line == "#include <...> search starts here:":
            in_search_list = True
        elif in_search_list and line == "End of search list.":
            complete = True
            break
        elif in_search_list:
            directory = ctx.path(line)
            if not line.startswith("/") or not directory.exists:
                fail("Invalid host GCC builtin include directory: %r" % line)
            directories.append(str(directory.realpath))
    ctx.delete("include_probe.cc")
    if not complete or not directories:
        fail("Could not detect host GCC builtin C++ include directories: %s" % result.stderr)
    return directories

def _tool_path(ctx, root, gcc, tool):
    candidate = root.get_child("bin/" + tool)
    if candidate.exists:
        return str(candidate)
    value = _execute(ctx, [gcc, "-print-prog-name=" + tool]).stdout.strip()
    if value.startswith("/") and ctx.path(value).exists:
        return value
    fail("Could not resolve host GCC tool %r under %s or through %s -print-prog-name" % (tool, root, gcc))

def _gcc_tool_path(ctx, root, gcc, tool, target, version):
    """Return the `tool` of the same GCC release as `gcc`.

    `cpp` and `gcov` belong to GCC, not binutils: where several releases are installed, the
    plain name may be another release's, and its gcov cannot read this compiler's coverage data.
    """
    major = version.split(".")[0]
    for name in gcc_tool_names(tool, target, major):
        candidate = root.get_child("bin/" + name)
        if not candidate.exists:
            continue
        result = ctx.execute([str(candidate), "--version"], environment = {"LC_ALL": "C"})
        if result.return_code == 0 and banner_major(result.stdout) == major:
            return str(candidate)
    return _tool_path(ctx, root, gcc, tool)

def host_cpu(os):
    """Return the GCC arch name (`x86_64`/`aarch64`) for a repository/module ctx `os`."""
    arch = _ARCHES.get(os.arch.lower())
    if not arch:
        fail("Unsupported host GCC architecture: %s" % os.arch)
    return arch

def fallback_host_cpu(os):
    """Return the GCC arch name of a host whose GCC is the fallback toolchain, or None.

    That is a supported Linux host that no hermetic archive runs on. Unlike `host_cpu` this
    never fails: it is evaluated for every build, on hosts that may not be using GCC at all.

    Args:
      os: A repository/module ctx `os`, or a struct with `name` and `arch`.

    Returns:
      `aarch64`, or None where an archive runs or the host is not supported.
    """
    if not os.name.lower().startswith("linux"):
        return None
    arch = _ARCHES.get(os.arch.lower())
    return None if arch == _HERMETIC_HOST_ARCH else arch

def fallback_cpu_constraint(arch):
    """Return the constraint that only the fallback toolchain's platform satisfies.

    Args:
      arch: `fallback_host_cpu` of the host.

    Returns:
      The `@platforms` CPU constraint label of a host with a fallback toolchain, else the one
      that no platform satisfies, so that its registered toolchain never matches.
    """
    return "@platforms//cpu:" + arch if arch else "@platforms//:incompatible"

def host_toolchain_names(modules, host, host_arch):
    """Return the names of the `toolchain` tags that `host` swaps for the host GCC.

    Only native-arch toolchains are swapped: by default the root module's own, or exactly
    those named in `host.toolchains` (which may belong to any module). Toolchains declared
    by dependencies, eg one used only for its `:libstdcxx`, otherwise stay hermetic.

    Args:
      modules: `module_ctx.modules`, or structs with `is_root` and `tags.toolchain`.
      host: The root module's `host` tag, or None.
      host_arch: The host GCC arch (`x86_64`/`aarch64`), or None without `host`.

    Returns:
      A list of toolchain names to provide from the host GCC.
    """
    if not host:
        return []
    return [
        tag.name
        for mod in modules
        for tag in mod.tags.toolchain
        if tag.arch == host_arch and (
            tag.name in host.toolchains if host.toolchains else mod.is_root
        )
    ]

def _installation(ctx, driver):
    """Return the directory that a GCC driver reports as its own, eg /usr/lib/gcc/<target>/13."""
    for line in _execute(ctx, [driver, "-print-search-dirs"]).stdout.split("\n"):
        if line.startswith(_INSTALL):
            return str(ctx.path(line[len(_INSTALL):].strip().rstrip("/")).realpath)
    fail("Could not detect where the host GCC %s is installed" % driver)

def _path_drivers(ctx, arch):
    """Return the installation prefix, `gcc` and `g++` of the GCC that `gcc` on PATH runs.

    PATH may reach it through a wrapper directory (eg ccache) or a versioned name, so the
    installation is the one the compiler reports, and the drivers are those under its prefix
    that belong to the same installation - not whatever `<prefix>/bin/gcc` happens to be.
    """
    found = ctx.which("gcc")
    if not found:
        fail("No hermetic GCC runs on %s hosts and no gcc was found on PATH: install GCC, or set gcc.host(path = ...)" % arch)
    installation = _installation(ctx, str(found))

    # <prefix>/lib/gcc/<target>/<version>
    root = ctx.path(installation).dirname.dirname.dirname.dirname
    target = _execute(ctx, [str(found), "-dumpmachine"]).stdout.strip()
    major = _execute(ctx, [str(found), "-dumpversion"]).stdout.strip().split(".")[0]
    drivers = []
    for name in ["gcc", "g++"]:
        driver = None
        for candidate in gcc_tool_names(name, target, major):
            path = root.get_child("bin/" + candidate)
            if path.exists and _installation(ctx, str(path)) == installation:
                driver = str(path)
                break
        if not driver:
            fail("Could not find the %s of the GCC that %s runs under %s/bin: set gcc.host(path = ...)" % (name, found, root))
        drivers.append(driver)
    return root, drivers[0], drivers[1]

def _gcc_host_repository_impl(ctx):
    if not ctx.os.name.lower().startswith("linux"):
        fail("The host GCC toolchain supports only native Linux hosts")
    arch = host_cpu(ctx.os)
    if arch != ctx.attr.arch:
        fail("The host GCC cannot provide a %s toolchain on a %s host" % (ctx.attr.arch, arch))
    if ctx.attr.path:
        if not ctx.attr.path.startswith("/"):
            fail("gcc.host path must be an absolute GCC installation prefix")
        root = ctx.path(ctx.attr.path)
        for driver in ["bin/gcc", "bin/g++"]:
            if not root.get_child(driver).exists:
                fail("gcc.host path %s has no %s" % (ctx.attr.path, driver))
        gcc = str(root.get_child("bin/gcc"))
        gxx = str(root.get_child("bin/g++"))
    else:
        root, gcc, gxx = _path_drivers(ctx, arch)
    version = _detect_version(ctx, gcc, ctx.attr.gcc_version)
    target = _execute(ctx, [gcc, "-dumpmachine"]).stdout.strip()
    if target.split("-")[0] != arch or "linux" not in target:
        fail("Host GCC target %r does not match the native Linux %s host" % (target, arch))
    includes = _builtin_include_directories(ctx, gxx)
    tool_paths = {"gcc": gcc}
    for tool in ["ar", "as", "dwp", "nm", "objcopy", "objdump", "strip"]:
        tool_paths[tool] = _tool_path(ctx, root, gcc, tool)
    for tool in ["cpp", "gcov"]:
        tool_paths[tool] = _gcc_tool_path(ctx, root, gcc, tool, target, version)
    tool_paths["ld"] = _tool_path(ctx, root, gcc, "ld.bfd")
    linker_directory = str(ctx.path(tool_paths["ld"]).dirname)
    identifier = "linux-%s-host-gcc-%s" % (arch, version)

    # Deliberately no `:libstdcxx` or `:libgcc` targets: consumers that need
    # GCC's runtime must use the hermetic toolchain, not host libraries.
    ctx.file("BUILD.bazel", """
load("@rules_cc//cc/toolchains:cc_toolchain.bzl", "cc_toolchain")
# buildifier: disable=bzl-visibility
load("@rules_cc//cc/private/toolchain:unix_cc_toolchain_config.bzl", "cc_toolchain_config")

package(default_visibility = ["//visibility:public"])

# Host tools and headers are outside the sandbox; this is not an RBE toolchain.
filegroup(name = "files")

cc_toolchain_config(
    name = "config",
    abi_libc_version = "local",
    abi_version = "local",
    compile_flags = ["-U_FORTIFY_SOURCE", "-fstack-protector", "-Wall", "-fno-omit-frame-pointer"],
    compiler = "gcc",
    coverage_compile_flags = ["--coverage"],
    coverage_link_flags = ["--coverage"],
    cpu = %r,
    cxx_builtin_include_directories = %r,
    dbg_compile_flags = ["-g"],
    host_system_name = "local",
    link_flags = [%r, "-fuse-ld=bfd", "-Wl,-z,relro,-z,now", "-pass-exit-codes"],
    link_libs = ["-l:libstdc++.a", "-lm"],
    opt_compile_flags = ["-g0", "-O2", "-D_FORTIFY_SOURCE=1", "-DNDEBUG", "-ffunction-sections", "-fdata-sections"],
    opt_link_flags = ["-Wl,--gc-sections"],
    supports_start_end_lib = False,
    target_libc = "local",
    target_system_name = %r,
    tool_paths = %r,
    toolchain_identifier = %r,
    unfiltered_compile_flags = [
        "-no-canonical-prefixes",
        "-fno-canonical-system-headers",
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\\"redacted\\"",
        "-D__TIME__=\\"redacted\\"",
        "-D__TIMESTAMP__=\\"redacted\\"",
    ],
)

cc_toolchain(
    name = "cc_toolchain",
    all_files = ":files",
    ar_files = ":files",
    as_files = ":files",
    compiler_files = ":files",
    dwp_files = ":files",
    linker_files = ":files",
    objcopy_files = ":files",
    strip_files = ":files",
    supports_param_files = True,
    toolchain_config = ":config",
    toolchain_identifier = %r,
)
""" % (
        "k8" if arch == "x86_64" else arch,
        includes,
        "-B" + linker_directory + "/",
        target,
        tool_paths,
        identifier,
        identifier,
    ))

gcc_host_repository = repository_rule(
    implementation = _gcc_host_repository_impl,
    environ = ["PATH"],
    local = True,
    attrs = {
        "arch": attr.string(mandatory = True, values = ["x86_64", "aarch64"]),
        "gcc_version": attr.string(default = ""),
        "path": attr.string(default = "", doc = "GCC installation prefix; empty uses the GCC that `gcc` on PATH runs."),
    },
)
