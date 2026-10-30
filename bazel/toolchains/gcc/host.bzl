"""Opt-in host GCC toolchain repository for `gcc_extension.host`.

This is only created when a root module explicitly declares `gcc.host(...)`.
The hermetic toolchain never falls back to host tools, headers or libraries.
"""

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

def host_cpu(os):
    """Return the GCC arch name (`x86_64`/`aarch64`) for a repository/module ctx `os`."""
    arch = os.arch.lower()
    if arch in ["x86_64", "amd64"]:
        return "x86_64"
    if arch in ["aarch64", "arm64"]:
        return "aarch64"
    fail("Unsupported host GCC architecture: %s" % arch)

def _gcc_host_repository_impl(ctx):
    if not ctx.os.name.lower().startswith("linux"):
        fail("gcc.host supports only native Linux hosts")
    arch = host_cpu(ctx.os)
    if arch != ctx.attr.arch:
        fail("gcc.host cannot provide a %s toolchain on a %s host" % (ctx.attr.arch, arch))
    if not ctx.attr.path.startswith("/"):
        fail("gcc.host path must be an absolute GCC installation prefix")
    root = ctx.path(ctx.attr.path)
    for driver in ["bin/gcc", "bin/g++"]:
        if not root.get_child(driver).exists:
            fail("gcc.host path %s has no %s" % (ctx.attr.path, driver))
    gcc = str(root.get_child("bin/gcc"))
    gxx = str(root.get_child("bin/g++"))
    version = _detect_version(ctx, gcc, ctx.attr.gcc_version)
    target = _execute(ctx, [gcc, "-dumpmachine"]).stdout.strip()
    if target.split("-")[0] != arch or "linux" not in target:
        fail("Host GCC target %r does not match the native Linux %s host" % (target, arch))
    includes = _builtin_include_directories(ctx, gxx)
    tool_paths = {"gcc": gcc}
    for tool in ["ar", "as", "cpp", "dwp", "gcov", "nm", "objcopy", "objdump", "strip"]:
        tool_paths[tool] = _tool_path(ctx, root, gcc, tool)
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
    local = True,
    attrs = {
        "arch": attr.string(mandatory = True, values = ["x86_64", "aarch64"]),
        "gcc_version": attr.string(default = ""),
        "path": attr.string(mandatory = True),
    },
)
