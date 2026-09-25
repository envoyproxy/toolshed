SUPPORTED_ARCHES = ["aarch64", "x86_64"]

BINS_RELEASE = "0.2.21"

LLVM_VERSION = "22.1.8"

V8_VERSION = "14.6.202.10"

# LLVM release archive checksums, used to fetch the distribution directly when
# building the minimal LLVM toolchain repos.
LLVM_DISTRIBUTIONS = {
    "LLVM-22.1.8-Linux-ARM64.tar.xz": "805efad2bb91cb4967fa569e0881d10c0f69c04461cf671cccbae19f547acc34",
    "LLVM-22.1.8-Linux-X64.tar.xz": "df0e1ecf16caf3489a272a5eea4eec9b0d82878f6477fa309504f918a0006384",
    "LLVM-22.1.8-macOS-ARM64.tar.xz": "f260f4f7c0d430828a81ae8a3826a1d63fc0963ec2459489308cc23b1f7eab4f",
}

VERSIONS = {
    "cmake": "3.23.2",
    "git": "2.55.0",
    "llvm": LLVM_VERSION,
    "sq": "1.4.0",
    "v8": V8_VERSION,
    "ninja": "1.12.0",
    "python": "3.12",
    "bins_release": BINS_RELEASE,
    "msan_libs_sha256": "9755683afc5550dedaa7a004523e2d422ea3ed7278c1f5cbb1342cbb14535ba5",
    "tsan_libs_sha256": "adb9d3a27bcbe88ebfd462b8e6eeb8d305ea44f5aac01336d9ce85b010794fa9",
    "libcxx_libs_sha256": {
        "aarch64": "b3bd8dfc1c250d5c2c36de174138ffef9754402b33e54abe9b5efb25982fa2f7",
        "x86_64": "e40f39338ffe561dfa26541557c9e548fc7760db9d99f7b6c5de237b725482aa",
    },

    # Darwin libc++ for cross-compilation (extracted from LLVM macOS release)
    "libcxx_libs_darwin_sha256": {
        "aarch64": "5ca0d502e914781891dce382fa5902beb60adde4e2928d138668c80e1ef4be04",
    },

    # macOS SDK sysroot for cross-compilation (extracted from Apple CLTools)
    "macos_sysroot_sha256": {
        "arm64": "a43a6ff24f731fee85ab0acf9ff9ec053e634c9168f9c844c6a1e437d0d050cd",
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
        "Linux-X64": "6cb4cca6df33be00c80fa1639062c973d1cafe4e7ad98a9b4bdf21bf9dec5806",
        "Linux-ARM64": "9a6cc0a84d524342e578db739b04e8a3875adb40b38887e4e074661e925f8a9c",
        "macOS-ARM64": "928e51aa7c97fbb8c5c50075118f4b36e36363b1a2c3af2dfef9aea1ef526ade",
    },
    "sq_sha256": {
        "Linux-X64": "bf865008e64daaea7207dd589ea27557c92b1ff5d5bc988427f070c64da3e0c9",
        "Linux-ARM64": "fd04277a3847288ae1c4ee92848eafa51ca2a422f2ec73f16389ebb280c6354b",
    },
    # Git prebuilt hashes keyed by the artifact platform suffix (linux-x86_64, linux-aarch64).
    "git_sha256": {
        "linux-x86_64": "35ecec697d06af954c3d9d015e5cd328a71a7ea849fa833f45450c3ffc883f34",
        "linux-aarch64": "21708e8d80aa9d367981ac3257010fc6fbcdb09a279ede3784c3ed3f3838d0cd",
    },
    "cacert": {
        "version": "2026-08-13",
        "sha256": "f66dff1bdf8f96060b8177976f8b7d9254bc89bc4db933d769f7384d28480bc9",
        "url": "https://curl.se/ca/cacert-{version}.pem",
    },

    # Glint binary hashes by architecture
    "glint_sha256": {
        "amd64": "76f79e440f65b1ca9bbf7c0f3f38b7733684820e8765e22a3c68d81526ed300e",
        "arm64": "85c71c9c3ad8fd83e649560e6d88574ea42f1f73c72d055c8661a82950b35bee",
    },

    # Wee8 prebuilt hashes by architecture and stdlib ABI flavour.
    # libcxx keeps the legacy unsuffixed artifact name; libstdcxx is suffixed.
    "wee8_sha256": {
        "x86_64": {
            "libcxx": "a9c87dc23cae39b5d0666b9b22f5faf4dc028cc10cca734268ec673e8eee6ea6",
            "libstdcxx": "b2584b813cbbe1dfce67aaf72e1c4a0a4d746c5fbee44064a5464be62edf4f4b",
        },
        "aarch64": {
            "libcxx": "96f3e3b7dceb2e5779ed067b76faea9cc4caa699658b3a7b5cedabd0d4e64197",
            "libstdcxx": "",
        },
    },

    # Sysroot hashes organized by glibc version, stdlib variant, and architecture
    # Format: sysroot_hashes[glibc_version][stdlib_variant][arch]
    # stdlib_variant is either "base" (no libstdc++) or the libstdc++ version (e.g., "13")
    "sysroot_hashes": {
        "2.31": {
            "base": {
                "amd64": "b15fe2bed311223fa98fea03a54bb5bef3808e8d8c4becd14bbe579930039302",
                "arm64": "b49ffc7a1f8016eb669c77626958397ecaa86eae21f86911ca79c73ac768d3f2",
            },
            "13": {
                "amd64": "7625512f6609535504c04544928103fd32ea24dde374ef0a806f1ab227c96ffc",
                "arm64": "deccbf6c39f77dc7cace1b1d1f550f67dd3db1912bd99a02f5b88a89b6e5a3ac",
            },
        },
        "2.28": {
            "base": {
                "amd64": "d4fb7aa5e4d4b864b87e590401e3f48e7fbfc9dc41d7e6a6fd11008ff66263cc",
                "arm64": "4daa3de33bd5463978017e279bebebad26d1281f1721ac0f1bdff78bc8a7b620",
            },
            "13": {
                "amd64": "7fcfc93653130adfb8de4ae1de457cba03d51a6afc726112064ac91622dc80ec",
                "arm64": "e9721bb09be40cc429d257b799afc6b94e4691d56fadad3c0e1d9a2aefe8d509",
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
        "sha256": "6cb4cca6df33be00c80fa1639062c973d1cafe4e7ad98a9b4bdf21bf9dec5806",
        "url": "https://github.com/{repo}/releases/download/bins-v{bins_release}/llvm-minimal-{version}-{download_suffix}.tar.zst",
        "strip_prefix": "llvm-minimal-{version}-{download_suffix}",
    },
    "llvm_minimal_linux_arm64": {
        "type": "http_archive",
        "repo": "envoyproxy/toolshed",
        "download_suffix": "Linux-ARM64",
        "version": LLVM_VERSION,
        "bins_release": BINS_RELEASE,
        "sha256": "9a6cc0a84d524342e578db739b04e8a3875adb40b38887e4e074661e925f8a9c",
        "url": "https://github.com/{repo}/releases/download/bins-v{bins_release}/llvm-minimal-{version}-{download_suffix}.tar.zst",
        "strip_prefix": "llvm-minimal-{version}-{download_suffix}",
    },
    "llvm_minimal_macos_arm64": {
        "type": "http_archive",
        "repo": "envoyproxy/toolshed",
        "download_suffix": "macOS-ARM64",
        "version": LLVM_VERSION,
        "bins_release": BINS_RELEASE,
        "sha256": "928e51aa7c97fbb8c5c50075118f4b36e36363b1a2c3af2dfef9aea1ef526ade",
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
        "version": "1.9.0",
        "sha256": "779b3280571647034931c7f9ce8ef3836bfc55d00d23e7dad5370151e1f7149e",
        "url": "https://github.com/{repo}/releases/download/v{version}/{name}-v{version}.tar.gz",
        "strip_prefix": "{name}-v{version}",
    },
}
