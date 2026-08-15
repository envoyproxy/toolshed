SUPPORTED_ARCHES = ["aarch64", "x86_64"]

BINS_RELEASE = "0.2.7"

LLVM_VERSION = "22.1.8"

V8_VERSION = "14.6.202.10"

# Extra distributions for versions not (yet) in toolchains_llvm's version table
LLVM_DISTRIBUTIONS = {
    "LLVM-22.1.8-Linux-ARM64.tar.xz": "805efad2bb91cb4967fa569e0881d10c0f69c04461cf671cccbae19f547acc34",
    "LLVM-22.1.8-Linux-X64.tar.xz": "df0e1ecf16caf3489a272a5eea4eec9b0d82878f6477fa309504f918a0006384",
    "LLVM-22.1.8-macOS-ARM64.tar.xz": "f260f4f7c0d430828a81ae8a3826a1d63fc0963ec2459489308cc23b1f7eab4f",
}

VERSIONS = {
    "cmake": "3.23.2",
    "llvm": LLVM_VERSION,
    "v8": V8_VERSION,
    "ninja": "1.12.0",
    "python": "3.12",
    "bins_release": BINS_RELEASE,
    "msan_libs_sha256": "d0bb453af4fdb003f988ff84af9e6da57ff5da15f2f805c5d6c67bf0c1a54524",
    "tsan_libs_sha256": "188e9aa22a189c88172cd9f9103ceec0c6f024483c070e6dacad6172b6a31c62",
    "libcxx_libs_sha256": {
        "aarch64": "b3bd8dfc1c250d5c2c36de174138ffef9754402b33e54abe9b5efb25982fa2f7",
        "x86_64": "e40f39338ffe561dfa26541557c9e548fc7760db9d99f7b6c5de237b725482aa",
    },

    # Darwin libc++ for cross-compilation (extracted from LLVM macOS release)
    "libcxx_libs_darwin_sha256": {
        "aarch64": "de0ecb9c26a83961d3892076a54659e2a0a191db64db818edf64fbdc724fb6b9",
    },

    # macOS SDK sysroot for cross-compilation (extracted from Apple CLTools)
    "macos_sysroot_sha256": {
        "arm64": "194cf63f00134824ce09ab484a56af959f9049359c349ba953bcd623296b0c18",
    },
    "macos_sdk_pkg": {
        "url": "https://swcdn.apple.com/content/downloads/52/01/082-41241-A_0747ZN8FHV/dectd075r63pppkkzsb75qk61s0lfee22j/CLTools_macOSNMOS_SDK.pkg",
        "sha256": "ba3453d62b3d2babf67f3a4a44e8073d6555c85f114856f4390a1f53bd76e24a",
        "user_agent": "Mozilla/5.0",
        "sdk_prefix": "Payload/Library/Developer/CommandLineTools/SDKs/MacOSX15.5.sdk",
    },
    "pkgutil": {
        "url": "https://github.com/cerisier/pkgutil/releases/download/v1.2.0/pkgutil_linux_amd64",
        "sha256": "3bcf79dbec6b7858ca0c1b6db03952ac122501a74073bac186c8080fcfb391fd",
    },

    # Minimal LLVM artifact hashes by platform
    # Keys match the platform suffix in artifact names (Linux-X64, Linux-ARM64, macOS-ARM64).
    # Empty strings are placeholders; the release (bazel/prepare) workflow fills them after release.
    "llvm_minimal_sha256": {
        "Linux-X64": "3055f223cb27740e319412303c8298787b78062839d8809b88b13c4d6bcd82ca",
        "Linux-ARM64": "b00ea67259e613907da30cb5d8290192b54ab656f4759ace6794f3e10de1d0ed",
        "macOS-ARM64": "04a2ac21e89a42dba532509ee67c246b71ec8a15c6cef0f2d63e349fb120934c",
    },

    # Glint binary hashes by architecture
    "glint_sha256": {
        "amd64": "67c91213b7ae3ebf37a59ccd9272d5b940d7a8c6557f36f3a0481b8fc80a0121",
        "arm64": "9961efa497a7637faba50450e10c7ec783d0813a61b974c7b7c83ab86a555a3e",
    },

    # Wee8 prebuilt hashes by architecture and stdlib ABI flavour.
    # libcxx keeps the legacy unsuffixed artifact name; libstdcxx is suffixed.
    "wee8_sha256": {
        "x86_64": {
            "libcxx": "4bb306264d85dc629e7bb03ede97064de6c2e6452044ef6e528f7e319f51d482",
            "libstdcxx": "9a92188a27c2b8f8ac0ff2548c259bd1ce375431af6ee7b67626d22745bd0f8a",
        },
        "aarch64": {
            "libcxx": "9c4ce19dd446f62791979e4cd03c2da4df43d035479820db5a4a35aee605c3d8",
            "libstdcxx": "",
        },
    },

    # Sysroot hashes organized by glibc version, stdlib variant, and architecture
    # Format: sysroot_hashes[glibc_version][stdlib_variant][arch]
    # stdlib_variant is either "base" (no libstdc++) or the libstdc++ version (e.g., "13")
    "sysroot_hashes": {
        "2.31": {
            "base": {
                "amd64": "b144e360f07d87407aba0c0fd73434955b2143f08652a11e811b451e6bf4b697",
                "arm64": "2e71ed77bdc34b4095fdd4862d1687f16406e5df95b1b94cab6e61408ad94a9b",
            },
            "13": {
                "amd64": "fe05fe5200c2854286f5d7c5680fa05d203bf9de247b6df8d4994945743c94ff",
                "arm64": "7a2781b72d55a178f57bb637b4c1e11f2703f2c8e6af221fc48c427f044aa839",
            },
        },
        "2.28": {
            "base": {
                "amd64": "e6c76b428c3b857528ac62aedb78698b5fcf6c8c38282add349391f7018ea5f9",
                "arm64": "50d957b88a50b44ac59679cca9c8285d422514615eebf19226d795720786d1c1",
            },
            "13": {
                "amd64": "e69c1164d27894cf8df54b08cc5a3dc3a6821baa6b2683f85bef8350e3b64f56",
                "arm64": "e949a44b7020a5a0c695380fda56980ec27b5636cf65d450f85114a308f782cf",
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
    },
    "llvm_minimal_linux_x64": {
        "type": "http_archive",
        "repo": "envoyproxy/toolshed",
        "download_suffix": "Linux-X64",
        "version": LLVM_VERSION,
        "bins_release": BINS_RELEASE,
        "sha256": "3055f223cb27740e319412303c8298787b78062839d8809b88b13c4d6bcd82ca",
        "url": "https://github.com/{repo}/releases/download/bins-v{bins_release}/llvm-minimal-{version}-{download_suffix}.tar.zst",
        "strip_prefix": "llvm-minimal-{version}-{download_suffix}",
    },
    "llvm_minimal_linux_arm64": {
        "type": "http_archive",
        "repo": "envoyproxy/toolshed",
        "download_suffix": "Linux-ARM64",
        "version": LLVM_VERSION,
        "bins_release": BINS_RELEASE,
        "sha256": "b00ea67259e613907da30cb5d8290192b54ab656f4759ace6794f3e10de1d0ed",
        "url": "https://github.com/{repo}/releases/download/bins-v{bins_release}/llvm-minimal-{version}-{download_suffix}.tar.zst",
        "strip_prefix": "llvm-minimal-{version}-{download_suffix}",
    },
    "llvm_minimal_macos_arm64": {
        "type": "http_archive",
        "repo": "envoyproxy/toolshed",
        "download_suffix": "macOS-ARM64",
        "version": LLVM_VERSION,
        "bins_release": BINS_RELEASE,
        "sha256": "04a2ac21e89a42dba532509ee67c246b71ec8a15c6cef0f2d63e349fb120934c",
        "url": "https://github.com/{repo}/releases/download/bins-v{bins_release}/llvm-minimal-{version}-{download_suffix}.tar.zst",
        "strip_prefix": "llvm-minimal-{version}-{download_suffix}",
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
