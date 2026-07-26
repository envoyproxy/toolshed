SUPPORTED_ARCHES = ["aarch64", "x86_64"]

# This is only used for cross-compilation (toolchains_llvm provides these otherwise)
LLVM_CXX_BUILD = """
filegroup(
    name = "libcxx",
    srcs = [
        "lib/{arch}-unknown-linux-gnu/libc++.a",
        "lib/{arch}-unknown-linux-gnu/libc++abi.a",
        "lib/{arch}-unknown-linux-gnu/libunwind.a",
    ],
    visibility = ["//visibility:public"],
)
filegroup(
    name = "compiler_rt",
    srcs = glob(["lib/clang/*/lib/{arch}-unknown-linux-gnu/libclang_rt.builtins.a"]),
    visibility = ["//visibility:public"],
)
filegroup(
    name = "config_site",
    srcs = ["include/{arch}-unknown-linux-gnu/c++/v1/__config_site"],
    visibility = ["//visibility:public"],
)
"""

LLVM_VERSION = "22.1.8"

# Extra distributions for versions not (yet) in toolchains_llvm's version table
LLVM_DISTRIBUTIONS = {
    "LLVM-22.1.8-Linux-ARM64.tar.xz": "805efad2bb91cb4967fa569e0881d10c0f69c04461cf671cccbae19f547acc34",
    "LLVM-22.1.8-Linux-X64.tar.xz": "df0e1ecf16caf3489a272a5eea4eec9b0d82878f6477fa309504f918a0006384",
    "LLVM-22.1.8-macOS-ARM64.tar.xz": "f260f4f7c0d430828a81ae8a3826a1d63fc0963ec2459489308cc23b1f7eab4f",
}

VERSIONS = {
    "cmake": "3.23.2",
    "llvm": LLVM_VERSION,
    "ninja": "1.12.0",
    "python": "3.12",
    "bins_release": "0.1.62",
    "msan_libs_sha256": "2da6ebb745363b2ac71854b7d03a47c3e1a7d343994f392880efe2b6249d5aa3",
    "tsan_libs_sha256": "99d023e4f65d5dd1f75a4a1424571d1d54c22687245d35a4c551829e3b34d9dd",

    "libcxx_libs_sha256": {
        "aarch64": "b3bd8dfc1c250d5c2c36de174138ffef9754402b33e54abe9b5efb25982fa2f7",
        "x86_64": "e40f39338ffe561dfa26541557c9e548fc7760db9d99f7b6c5de237b725482aa",
    },

    # Darwin libc++ for cross-compilation (extracted from LLVM macOS release)
    "libcxx_libs_darwin_sha256": {
        "aarch64": "",
    },

    # macOS SDK sysroot for cross-compilation (extracted from Apple CLTools)
    "macos_sysroot_sha256": {
        "arm64": "",
    },

    # Glint binary hashes by architecture
    "glint_sha256": {
        "amd64": "67c91213b7ae3ebf37a59ccd9272d5b940d7a8c6557f36f3a0481b8fc80a0121",
        "arm64": "9961efa497a7637faba50450e10c7ec783d0813a61b974c7b7c83ab86a555a3e",
    },

    # Sysroot hashes organized by glibc version, stdlib variant, and architecture
    # Format: sysroot_hashes[glibc_version][stdlib_variant][arch]
    # stdlib_variant is either "base" (no libstdc++) or the libstdc++ version (e.g., "13")
    "sysroot_hashes": {
        "2.31": {
            "base": {
                "amd64": "06f521b99dd67cbe263a9e4e66be6777a2d1647540b519452f2fb3eb6e768631",
                "arm64": "a974bd1f8924ddfdf22db45365605a88da8b1ac865e4fe1c7b35a9ca82e44191",
            },
            "13": {
                "amd64": "9cec0bc6dd119c021f0bc840fe54a9804ec01fc2eb82cf7ef3bcb4edcc4aff93",
                "arm64": "8f7fba56ae74517d234725f2535dc39361028cb892893c8694e6e92bed132437",
            },
        },
        "2.28": {
            "base": {
                "amd64": "39917db8ad649e6780567cb83f6128a785a73f3862552b53b82a10d5f68ddcb6",
                "arm64": "a6912c2c0e0b485c609a2883ddf5d88bfd06f5c2eed9c15a3d870d6886f8b3ed",
            },
            "13": {
                "amd64": "060e7d63946ee579f6b6e8bb0b18e1fd957c138ada1518053e2b58baaae5401d",
                "arm64": "2f022becf7bb41f6c543f905c4a57576fea88a3e758480d05ca1abecb6b2732b",
            },
        },
    },

    # external archives
    "aspect_bazel_lib": {
        "type": "github_archive",
        "repo": "aspect-build/bazel-lib",
        "version": "2.16.0",
        "sha256": "092f841dd9ea8e736ea834f304877a25190a762d0f0a6c8edac9f94aac8bbf16",
        "strip_prefix": "bazel-lib-{version}",
        "url": "https://github.com/{repo}/archive/v{version}.tar.gz",
    },
    "bazel_features": {
        "type": "github_archive",
        "repo": "bazel-contrib/bazel_features",
        "strip_prefix": "bazel_features-{version}",
        "version": "1.43.0",
        "sha256": "c26b4e69cf02fea24511a108d158188b9d8174426311aac59ce803a78d107648",
        "url": "https://github.com/{repo}/releases/download/v{version}/bazel_features-v{version}.tar.gz",
    },
    "bazel_skylib": {
        "type": "github_archive",
        "repo": "bazelbuild/bazel-skylib",
        "version": "1.9.2",
        "sha256": "37cdfbc6faefea94f7b37760a305c98c08981116c2bc9e821e3b423221fad8c8",
        "url": "https://github.com/{repo}/releases/download/{version}/bazel-skylib-{version}.tar.gz",
    },
    "llvm_libcxx_aarch64": {
        "arch": "aarch64",
        "type": "http_archive",
        "repo": "llvm/llvm-project",
        "download_suffix": "Linux-ARM64",
        "version": LLVM_VERSION,
        "sha256": "805efad2bb91cb4967fa569e0881d10c0f69c04461cf671cccbae19f547acc34",
        "url": "https://github.com/{repo}/releases/download/llvmorg-{version}/LLVM-{version}-{download_suffix}.tar.xz",
        "strip_prefix": "LLVM-{version}-{download_suffix}/",
        "build_file_content": LLVM_CXX_BUILD,
    },
    "llvm_libcxx_x86_64": {
        "arch": "x86_64",
        "download_suffix": "Linux-X64",
        "type": "http_archive",
        "repo": "llvm/llvm-project",
        "version": LLVM_VERSION,
        "sha256": "df0e1ecf16caf3489a272a5eea4eec9b0d82878f6477fa309504f918a0006384",
        "url": "https://github.com/{repo}/releases/download/llvmorg-{version}/LLVM-{version}-{download_suffix}.tar.xz",
        "strip_prefix": "LLVM-{version}-{download_suffix}/",
        "build_file_content": LLVM_CXX_BUILD,
    },
    "llvm_source": {
        "type": "github_archive",
        "repo": "llvm/llvm-project",
        "version": "llvmorg-%s" % LLVM_VERSION,
        "sha256": "ad18b70e287954c3d62bc7e0b86e7b7af2adf87bcfce21c15fe717f101d7aace",
        "url": "https://github.com/{repo}/archive/{version}.tar.gz",
        "strip_prefix": "llvm-project-{version}",
        "build_file_content": """filegroup(name = \"all\", srcs = glob([\"**\"]), visibility = [\"//visibility:public\"])""",
    },
    "rules_python": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_python",
        "version": "1.4.1",
        "sha256": "9f9f3b300a9264e4c77999312ce663be5dee9a56e361a1f6fe7ec60e1beef9a3",
        "url": "https://github.com/{repo}/releases/download/{version}/{name}-{version}.tar.gz",
        "strip_prefix": "{name}-{version}",
    },
    "rules_cc": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_cc",
        "version": "0.2.17",
        "sha256": "283fa1cdaaf172337898749cf4b9b1ef5ea269da59540954e51fba0e7b8f277a",
        "url": "https://github.com/{repo}/releases/download/{version}/{name}-{version}.tar.gz",
        "strip_prefix": "{name}-{version}",
    },
    "rules_foreign_cc": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_foreign_cc",
        "version": "0.14.0",
        "sha256": "e0f0ebb1a2223c99a904a565e62aa285bf1d1a8aeda22d10ea2127591624866c",
        "url": "https://github.com/{repo}/releases/download/{version}/{name}-{version}.tar.gz",
        "strip_prefix": "{name}-{version}",
    },
    "rules_perl": {
        "type": "github_archive",
        "repo": "bazel-contrib/rules_perl",
        "version": "0.4.1",
        "sha256": "e09ba7ab6a52059a5bec71cf9a8a5b4e512c8592eb8d15af94ed59e048a2ec6d",
        "url": "https://github.com/{repo}/archive/refs/tags/{version}.tar.gz",
        "strip_prefix": "{name}-{version}",
    },
    "rules_pkg": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_pkg",
        "version": "1.1.0",
        "sha256": "b7215c636f22c1849f1c3142c72f4b954bb12bb8dcf3cbe229ae6e69cc6479db",
        "url": "https://github.com/{repo}/releases/download/{version}/{name}-{version}.tar.gz",
    },
    "rules_license": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_license",
        "version": "0.0.7",
        "sha256": "4531deccb913639c30e5c7512a054d5d875698daeb75d8cf90f284375fe7c360",
        "url": "https://github.com/{repo}/releases/download/{version}/{name}-{version}.tar.gz",
    },
    "rules_shell": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_shell",
        "version": "0.6.1",
        "sha256": "e6b87c89bd0b27039e3af2c5da01147452f240f75d505f5b6880874f31036307",
        "url": "https://github.com/{repo}/releases/download/v{version}/{name}-v{version}.tar.gz",
        "strip_prefix": "{name}-{version}",
    },
    "toolchains_llvm": {
        "type": "github_archive",
        "patch_args": ["-p1"],
        "patches": ["@envoy_toolshed//:patches/toolchains_llvm.patch"],
        "repo": "bazel-contrib/toolchains_llvm",
        "version": "1.8.0",
        "sha256": "3b05826f256040f91c24dcaad673eb1c91e4cc93f4043d0205f2512327640205",
        "url": "https://github.com/{repo}/releases/download/v{version}/{name}-v{version}.tar.gz",
        "strip_prefix": "{name}-v{version}",
    },
}
