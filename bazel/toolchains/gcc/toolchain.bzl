# buildifier: disable=bzl-visibility
load(
    "@rules_cc//cc/private/toolchain:unix_cc_toolchain_config.bzl",
    gcc_cc_toolchain_config = "cc_toolchain_config",
)

_GCC_VERSIONS = [
    "13",
    "12",
    "11",
    "10",
]

def _builtin_include_directories(triple):
    return (
        ["/usr/include/{}/c++/{}".format(triple, version) for version in _GCC_VERSIONS] +
        ["/usr/lib/gcc/{}/{}/include".format(triple, version) for version in _GCC_VERSIONS] +
        ["/usr/include/c++/{}".format(version) for version in _GCC_VERSIONS] +
        ["/usr/include/c++/{}/backward".format(version) for version in _GCC_VERSIONS] +
        [
            "/usr/local/include",
            "/usr/include/{}".format(triple),
            "/usr/include",
            "/usr/lib/linux/uapi",
        ]
    )

_TOOL_PATHS = {
    "ar": "/usr/bin/ar",
    "cpp": "/usr/bin/cpp",
    "dwp": "/usr/bin/dwp",
    "gcc": "/usr/bin/gcc",
    "gcov": "/usr/bin/gcov",
    "ld": "/usr/bin/ld",
    "nm": "/usr/bin/nm",
    "objcopy": "/usr/bin/objcopy",
    "objdump": "/usr/bin/objdump",
    "strip": "/usr/bin/strip",
}

_TOOLCHAIN_CONFIGS = {
    "x86_64": {
        "abi_libc_version": "glibc_2.39",
        "abi_version": "gcc-13",
        "cpu": "k8",
        "cxx_builtin_include_directories": _builtin_include_directories("x86_64-linux-gnu"),
        "target_system_name": "x86_64-linux-gnu",
        "toolchain_identifier": "linux-x86_64-gcc-13",
    },
    "aarch64": {
        "abi_libc_version": "glibc_2.39",
        "abi_version": "gcc-13",
        "cpu": "aarch64",
        "cxx_builtin_include_directories": _builtin_include_directories("aarch64-linux-gnu"),
        "target_system_name": "aarch64-linux-gnu",
        "toolchain_identifier": "linux-aarch64-gcc-13",
    },
}

def gcc_linux_cc_toolchain_config(name, arch):
    config = _TOOLCHAIN_CONFIGS[arch]

    gcc_cc_toolchain_config(
        name = name,
        abi_libc_version = config["abi_libc_version"],
        abi_version = config["abi_version"],
        compiler = "gcc",
        cpu = config["cpu"],
        cxx_builtin_include_directories = config["cxx_builtin_include_directories"],
        dbg_compile_flags = ["-g"],
        host_system_name = arch,
        link_flags = [
            "-Wl,--build-id=md5",
            "-Wl,--hash-style=gnu",
            "-Wl,-z,relro,-z,now",
        ],
        link_libs = [
            "-lstdc++",
            "-lm",
        ],
        opt_compile_flags = [
            "-O2",
            "-DNDEBUG",
        ],
        supports_start_end_lib = True,
        target_libc = "glibc",
        target_system_name = config["target_system_name"],
        tool_paths = _TOOL_PATHS,
        toolchain_identifier = config["toolchain_identifier"],
    )
