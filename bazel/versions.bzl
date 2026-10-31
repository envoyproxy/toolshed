SUPPORTED_ARCHES = ["aarch64", "x86_64"]

BINS_RELEASE = "0.2.30"

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
    "gcc_toolchain": {
        "version": "13.4.0",
        "release": "18082025",
        "sha256": {
            "x86_64": "d96071c1b98499afd7b7b56ebd69ad414020edf66e982004acffe7df8aaf7e02",
            "aarch64": "770cf6bf62bdf78763de526d3a9f5cae4c19f1a3aca0ef8f18b05f1a46d1ffaf",
        },
    },
    "cmake": "3.23.2",
    "git": "2.55.0",
    "hunspell": {
        "version": "1.7.6",
        "sha256": "9c650ace31d4d8cc1da925a9507c3de1d50f1a54857af2f72429f517d5d53467",
    },
    "dictionary_en": {
        "version": "4.0.0",
        "sha256": "160cba5e6c0230d43d70b0c929e498566ff2c3c4bcf840318d98ce28e31ee756",
    },
    "llvm": LLVM_VERSION,
    "sq": "1.4.0",
    "v8": V8_VERSION,
    "ninja": "1.12.0",
    "python": "3.12",
    "bins_release": BINS_RELEASE,
    "msan_libs_sha256": "f054293360a932993602265ea6c52e777c4f89eaff46cec4d80e96aa75805e4a",
    "tsan_libs_sha256": "adf08795dcbb432cb4cb24b8301c0867fe11d69ccac14d70ba7c4e5d6ab3dd2b",
    # Filled after the bins-v* release publishes the shared libunwind artifact.
    "unwind_libs_sha256": "a4cb98a8ceb7eb81eb5346703d30636db85ecfc7ed876983a24cbf56af8f2b8e",
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
        "Linux-X64": "a12891b93faaf8fc1293db6232bf71fcdade9df10e978fe92dbac78d7379130d",
        "Linux-ARM64": "a4a8a3545ca213117e9629aa4b0abd6fd1232556109af31b3dacf16b1b59ffa1",
        "macOS-ARM64": "ca6c644a6d285d52d62bf7cb206d839623668eaf86cdc25bc0a709cd137a2017",
    },
    "sq_sha256": {
        "Linux-X64": "82c13d003a924b5560822f363df1af7733839cd82546a3074b2a32de0c5e99fb",
        "Linux-ARM64": "b0520af4b16d4ee5efaf4ecfbea2d60d6de11e29dcd003924d191a315cb211ae",
    },
    # Hunspell prebuilt hashes keyed by the artifact platform suffix (linux-x86_64, linux-aarch64),
    # filled by the release preparation once a bins-v* release publishes the artifacts.
    "hunspell_sha256": {
        "linux-x86_64": "",
        "linux-aarch64": "",
    },
    # Git prebuilt hashes keyed by the artifact platform suffix (linux-x86_64, linux-aarch64).
    "git_sha256": {
        "linux-x86_64": "e64a3bac2d21552076b7dfe6e09d08f873d9391f38818f9bf2f9ea1aa4b2ebb1",
        "linux-aarch64": "a0618fbe88c742faa7954f72d5e630c9644fc4b1909614f9cd21353f194b116b",
    },
    "cacert": {
        "version": "2026-08-13",
        "sha256": "f66dff1bdf8f96060b8177976f8b7d9254bc89bc4db933d769f7384d28480bc9",
        "url": "https://curl.se/ca/cacert-{version}.pem",
    },

    # Glint binary hashes by architecture
    "glint_sha256": {
        "amd64": "1d93c22b11dcf3b2c62e7ae39463df137fea394a2f2a22d22f8f4354bb7ef6d8",
        "arm64": "206776e11414bb07c48b5a92f1efd684a3ce948e24b927e0a86b53d7520b2852",
    },

    # Wee8 prebuilt hashes by architecture and stdlib ABI flavour.
    # libcxx keeps the legacy unsuffixed artifact name; libstdcxx is suffixed.
    # TODO: refresh both libstdcxx hashes in the next bins-v* release, built
    # with hermetic GCC and the base glibc 2.31 sysroot, before downstream use.
    "wee8_sha256": {
        "x86_64": {
            "libcxx": "ce217d16544fb3fd2cecce3cf872a6ad82902117297b88a223aec5c81bc521df",
            "libstdcxx": "0ca4fbbab6d7f3ac52efce3834e435945d14e1f45b02daed7c7454ab5e074a51",
        },
        "aarch64": {
            "libcxx": "682d0926e555da2fb33c7dc6dc95f884790fce5bc49fd95ca88a121e857d71a5",
            "libstdcxx": "a6cbe6e6212412ee180479358c58af3d15f90d306baf46fef1994f2ddf445def",
        },
    },

    # Sysroot hashes organized by glibc version, stdlib variant, and architecture.
    # Format: sysroot_hashes[glibc_version][stdlib_variant][arch]
    # stdlib_variant is "base" or the libstdc++ version (e.g., "13").
    "sysroot_hashes": {
        "2.31": {
            "base": {
                "amd64": "add77f0ac28e64e84236cec34d85a551a784cd1f734ab584c82247840a8cd1bb",
                "arm64": "ab81edf74e3293827eb6eba5885a3ccc6c592b5d14b5322f2afcf25941f25ea8",
            },
            "13": {
                "amd64": "9c9f98e44d1e3a6223324f36344e3449a0ff60ea9e44fbfa8c0e5015dea922a3",
                "arm64": "8bcef528464e1a58d72faee1e2824ed8d3c4896ab36d493a95cebe7f98314257",
            },
        },
        "2.28": {
            "base": {
                "amd64": "b0c96226d4ad4638dae913767413243b31170beec798a887526171b03f6dd35b",
                "arm64": "cb7b639f42811ce360e0a2b96e7c8fb99bc70e5bf16ced4ffdd6ac0f0b26558a",
            },
            "13": {
                "amd64": "9f3e17744bb767894356f470373e73e2395a21ba8ee65949291cdc167b2977c6",
                "arm64": "3d7a94fa0046454682f376ec577da50da8fbfe9eb67edd9b3c63dac7d55ae1df",
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
        "sha256": "a12891b93faaf8fc1293db6232bf71fcdade9df10e978fe92dbac78d7379130d",
        "url": "https://github.com/{repo}/releases/download/bins-v{bins_release}/llvm-minimal-{version}-{download_suffix}.tar.zst",
        "strip_prefix": "llvm-minimal-{version}-{download_suffix}",
    },
    "llvm_minimal_linux_arm64": {
        "type": "http_archive",
        "repo": "envoyproxy/toolshed",
        "download_suffix": "Linux-ARM64",
        "version": LLVM_VERSION,
        "bins_release": BINS_RELEASE,
        "sha256": "a4a8a3545ca213117e9629aa4b0abd6fd1232556109af31b3dacf16b1b59ffa1",
        "url": "https://github.com/{repo}/releases/download/bins-v{bins_release}/llvm-minimal-{version}-{download_suffix}.tar.zst",
        "strip_prefix": "llvm-minimal-{version}-{download_suffix}",
    },
    "llvm_minimal_macos_arm64": {
        "type": "http_archive",
        "repo": "envoyproxy/toolshed",
        "download_suffix": "macOS-ARM64",
        "version": LLVM_VERSION,
        "bins_release": BINS_RELEASE,
        "sha256": "ca6c644a6d285d52d62bf7cb206d839623668eaf86cdc25bc0a709cd137a2017",
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
