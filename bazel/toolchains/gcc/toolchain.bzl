"""Configure GCC with its own C++ runtime and toolshed's shared libc sysroot."""

# buildifier: disable=bzl-visibility
load(
    "@rules_cc//cc/private/toolchain:unix_cc_toolchain_config.bzl",
    gcc_cc_toolchain_config = "cc_toolchain_config",
)

def gcc_linux_cc_toolchain_config(name, arch, triple, version, sysroot):
    """Configure an extracted Linux cross compiler, never the host compiler.

    Args:
        name: Configuration target name.
        arch: Target CPU.
        triple: GCC's configured target triple.
        version: GCC version.
        sysroot: Label exporting the base glibc sysroot.
    """
    root = native.package_relative_label(":BUILD.bazel").workspace_root
    sysroot = Label(sysroot)
    sysroot_path = sysroot.workspace_root + "/" + sysroot.package
    gcc_lib = root + "/lib/gcc/" + triple + "/" + version
    cxx_include = root + ("/aarch64-linux" if arch == "aarch64" else "") + "/include/c++/" + version
    # -nostdinc removes GCC's configured archive/host include search. -idirafter
    # restores only these compiler headers and base-sysroot libc headers, after
    # project -I/-isystem paths (including the explicit C++ headers below).
    c_includes = [
        gcc_lib + "/include",
        gcc_lib + "/include-fixed",
        sysroot_path + "/usr/include",
        sysroot_path + "/usr/include/" + arch + "-linux-gnu",
    ]
    cxx_includes = [
        cxx_include,
        cxx_include + "/" + triple,
        cxx_include + "/backward",
    ]
    lib_dirs = [
        gcc_lib,
        root + "/lib",
        root + "/lib64",
        root + "/" + triple + "/lib",
        root + "/" + triple + "/lib64",
        sysroot_path + "/usr/lib/" + arch + "-linux-gnu",
        sysroot_path + "/lib/" + arch + "-linux-gnu",
    ]
    # -B selects bundled assembler/linker executables and startup objects.
    # crtbegin/crtend come from gcc_lib; crt1/Scrt1, crti and crtn must instead
    # come from the base sysroot's multiarch lib directories. -L repeats those
    # paths for ld's libraries; unlike -B it does not control startup objects.
    # --sysroot alone does not add Debian's usr/lib/<arch>-linux-gnu layout to
    # these archives' configured GCC search paths, hence the explicit -B/-L.
    search_flags = ["--sysroot=" + sysroot_path, "-B" + root + "/bin/"]
    search_flags += ["-B" + directory + "/" for directory in lib_dirs]
    gcc_cc_toolchain_config(
        name = name,
        abi_libc_version = "glibc_2.31",
        abi_version = "gcc-" + version,
        builtin_sysroot = sysroot_path,
        compiler = "gcc",
        compile_flags = search_flags + ["-nostdinc"] + ["-idirafter" + directory for directory in c_includes],
        cpu = "k8" if arch == "x86_64" else arch,
        cxx_builtin_include_directories = ["%workspace%/" + directory for directory in cxx_includes + c_includes],
        cxx_flags = ["-nostdinc++"] + ["-isystem" + directory for directory in cxx_includes],
        dbg_compile_flags = ["-g"],
        host_system_name = "x86_64-linux",
        link_flags = search_flags + ["-L" + directory for directory in lib_dirs] + [
            "-static-libgcc",
            "-Wl,--build-id=md5",
            "-Wl,--hash-style=gnu",
            "-Wl,-z,relro,-z,now",
        ],
        # xbin/gcc is the C driver: -static-libstdc++ has no effect on explicit
        # -lstdc++, so select the archive by name instead.
        link_libs = ["-l:libstdc++.a", "-lm"],
        opt_compile_flags = ["-O2", "-DNDEBUG"],
        # The bundled GNU BFD linker does not support --start-lib/--end-lib.
        supports_start_end_lib = False,
        target_libc = "glibc",
        target_system_name = triple,
        tool_paths = {tool: "xbin/" + tool for tool in [
            "ar",
            "cpp",
            "dwp",
            "gcc",
            "gcov",
            "ld",
            "nm",
            "objcopy",
            "objdump",
            "strip",
        ]},
        toolchain_identifier = "linux-" + arch + "-gcc-" + version,
    )
