
VERSIONS = {
    "cmake": "3.23.2",
    "llvm": "18.1.8",
    "ninja": "1.12.0",
    "python": "3.12",

    "bins_release": "0.1.21",
    "msan_libs_sha256": "2747f66b447af7c422d7db0bfca7147e197ff0ebe7500f10388ade2f9265a359",
    "tsan_libs_sha256": "9fb57a2b209e766487f00456d05462cb7030549b22f7885cfd6d89d448d40ee8",

    # Sysroot hashes organized by glibc version, stdlib variant, and architecture
    # Format: sysroot_hashes[glibc_version][stdlib_variant][arch]
    # stdlib_variant is either "base" (no libstdc++) or the libstdc++ version (e.g., "13")
    "sysroot_hashes": {
        "2.31": {
            "base": {
                "amd64": "464802e4c1eadc3297f8e3c033325a1c0e32097fb4ed56c9df9dec9a41fe8ecd",
                "arm64": "2dabcf9623c40207c14b441ab394c60e6f79fbdf1e53c98f04df7525eb001a6a",
            },
            "13": {
                "amd64": "a02b8045b59f425cf3f7200abaf03745b03fa213d6592d10c4ec722d83525555",
                "arm64": "0eda7b5ba799bd24b37f4837356d8b0b6a1887c3cf505772018bc2e7c14e5cfd",
            },
        },
        "2.28": {
            "base": {
                "amd64": "ce0d09eb5b6e4c47871b0e92870bb5426de9ef6459fcb22edce2be9424880bfe",
                "arm64": "0d816b8ac2643ddb84e58760f416dc6e56094bb2fa1c8dd71122a5fb9a6d560c",
            },
            "13": {
                "amd64": "313a91586621c2ee5417ae6a9e387b94ab92b9fc9d75dbca3b17ae5f7e1b9ee8",
                "arm64": "1326247965b804163614249b1f228e6239f8c1369aaa862cfdde8b6d13fc66c4",
            },
        },
    },

    # Legacy hash keys for backward compatibility (default: glibc 2.31 with libstdc++13)
    "sysroot_amd64_sha256": "a02b8045b59f425cf3f7200abaf03745b03fa213d6592d10c4ec722d83525555",
    "sysroot_arm64_sha256": "0eda7b5ba799bd24b37f4837356d8b0b6a1887c3cf505772018bc2e7c14e5cfd",

    "aspect_bazel_lib": {
        "type": "github_archive",
        "repo": "aspect-build/bazel-lib",
        "version": "2.16.0",
        "sha256": "092f841dd9ea8e736ea834f304877a25190a762d0f0a6c8edac9f94aac8bbf16",
        "strip_prefix": "bazel-lib-{version}",
        "url": "https://github.com/{repo}/archive/v{version}.tar.gz",
    },

    "bazel_skylib": {
        "type": "github_archive",
        "repo": "bazelbuild/bazel-skylib",
        "version": "1.4.2",
        "sha256": "66ffd9315665bfaafc96b52278f57c7e2dd09f5ede279ea6d39b2be471e7e3aa",
        "url": "https://github.com/{repo}/releases/download/{version}/bazel-skylib-{version}.tar.gz",
    },

    "llvm_source": {
        "type": "github_archive",
        "repo": "llvm/llvm-project",
        "version": "llvmorg-18.1.8",
        "sha256": "09c08693a9afd6236f27a2ebae62cda656eba19021ef3f94d59e931d662d4856",
        "url": "https://github.com/{repo}/archive/{version}.tar.gz",
        "strip_prefix": "llvm-project-{version}",
        "build_file_content": """filegroup(name = \"all\", srcs = glob([\"**\"]), visibility = [\"//visibility:public\"])""",
    },

    "org_chromium_sysroot_linux_x64": {
        "type": "github_archive",
        "sha256": "5df5be9357b425cdd70d92d4697d07e7d55d7a923f037c22dc80a78e85842d2c",
        "version": "bullseye",
        "url": "https://commondatastorage.googleapis.com/chrome-linux-sysroot/toolchain/4f611ec025be98214164d4bf9fbe8843f58533f7/debian_{version}_amd64_sysroot.tar.xz",
        "build_file_content": """filegroup(
    name = "sysroot",
    srcs = glob(["**"]),
    visibility = ["//visibility:public"],
)""",
    },

    "rules_python": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_python",
        "version": "1.4.1",
        "sha256": "9f9f3b300a9264e4c77999312ce663be5dee9a56e361a1f6fe7ec60e1beef9a3",
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

    "toolchains_llvm": {
        "type": "github_archive",
        "repo": "bazel-contrib/toolchains_llvm",
        "version": "1.4.0",
        "sha256": "fded02569617d24551a0ad09c0750dc53a3097237157b828a245681f0ae739f8",
        "url": "https://github.com/{repo}/releases/download/v{version}/{name}-v{version}.tar.gz",
        "strip_prefix": "{name}-v{version}",
    },
}
