SUPPORTED_ARCHES = ["aarch64", "x86_64"]

BINS_RELEASE = "0.2.27"

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
    "llvm": LLVM_VERSION,
    "sq": "1.4.0",
    "v8": V8_VERSION,
    "ninja": "1.12.0",
    "python": "3.12",
    "bins_release": BINS_RELEASE,
    "msan_libs_sha256": "5538945e7113677fe90ea809bc15e90c4c573370e76eadf9c432b6936776d2e7",
    "tsan_libs_sha256": "07f78bcfba0c6be156a893ec4e5fe27a34fd3e69ef616ae989d21ab006d41b57",
    # Filled after the bins-v* release publishes the shared libunwind artifact.
    "unwind_libs_sha256": "f8f031cd252cdfd59308d2f50dd0e4cea8952e6769fb348d8293d33e19647bee",
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
        "amd64": "50e0a0d96d3185fa4b5fda0c71e7bf2afc173abc635bb9ea1a00d6319ec97d18",
        "arm64": "b0af7226dc726d82a92ac23320167595c6069fed9f3fb9d207bcf08dc52a94e9",
    },

    # Wee8 prebuilt hashes by architecture and stdlib ABI flavour.
    # libcxx keeps the legacy unsuffixed artifact name; libstdcxx is suffixed.
    # TODO: refresh both libstdcxx hashes in the next bins-v* release, built
    # with hermetic GCC and the base glibc 2.31 sysroot, before downstream use.
    "wee8_sha256": {
        "x86_64": {
            "libcxx": "ce217d16544fb3fd2cecce3cf872a6ad82902117297b88a223aec5c81bc521df",
            "libstdcxx": "ad9895c550bdf8f4de931c0143c99cc28ae38aa0b475bc4602e494eedac46e90",
        },
        "aarch64": {
            "libcxx": "682d0926e555da2fb33c7dc6dc95f884790fce5bc49fd95ca88a121e857d71a5",
            "libstdcxx": "",
        },
    },

    # Sysroot hashes organized by glibc version, stdlib variant, and architecture.
    # Format: sysroot_hashes[glibc_version][stdlib_variant][arch]
    # stdlib_variant is "base" or the libstdc++ version (e.g., "13").
    "sysroot_hashes": {
        "2.31": {
            "base": {
                "amd64": "c027659e4ed93c2f53ca29cc611962790cde21289cbedcfd3419354d6a50767e",
                "arm64": "33fb571b3b9b5edb9854fa4444719fae01c0c08825b3051357fcd4ab3721749a",
            },
            "13": {
                "amd64": "0562bde13b68aa1c49ab286c5bb765158a9f17fb69f3f1d190672ef171502dbf",
                "arm64": "db9c5b96cd4ecc9b5ec4ac865d5e91eacf2020ef583aa262c6a906741f46ca11",
            },
        },
        "2.28": {
            "base": {
                "amd64": "d7ea7bc466377b2294127875216a701e400a57445b1c8daca223c71445681fc1",
                "arm64": "ae47a5b829fa354d1936e97c3c01aca3b3fa49546717809f1618a2c20d9ff5f2",
            },
            "13": {
                "amd64": "b0a230b3875f36dc50739fb4711e8745a0b65fd1b1e4d0c4961c6832980c0510",
                "arm64": "8fd6257c1a6ea3048d03d46e3a452873f885fd17ced5640deb3b3994c8dda4bf",
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
