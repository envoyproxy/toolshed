
VERSION_LIBTOOL = "2.5.4"

VERSIONS = {
    "cmake": "3.23.2",
    "llvm": "18.1.8",
    "ninja": "1.12.0",
    "python": "3.12",
    "libtool": VERSION_LIBTOOL,

    "bins_release": "0.1.6",
    "msan_libs_sha256": "a093b090552afaea86577c69ef202df7230778f878557caa0292fffa69bf94d4",
    "tsan_libs_sha256": "2bb532df43bb816784fbbb911e68f40a731d78ad53eacc100b6595899e11b9ff",
    "sysroot_amd64_sha256": "b16027eaf1820faa8f31d3aad9918f17bb3a469e9c91ab2bae44ba41dbd42956",
    "sysroot_arm64_sha256": "4492a91f7daa0c8400aaf33d9ed392dd5662a55e7df45fd6c45f4f34f3254fff",
    "libtool_aarch64_sha256": "96eeafc3ee27fbb88a71e5949cd7c6903eadf050a5b7878ac695ff1aa7ece0d9",
    "libtool_x86_64_sha256": "39c6dd9c25569fee5ae82df78aa88c3876e3b2e793899164a2cdfec7fca5d161",

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
        "version": "1.0.0",
        "sha256": "4f7e2aa1eb9aa722d96498f5ef514f426c1f55161c3c9ae628c857a7128ceb07",
        "url": "https://github.com/{repo}/releases/download/{version}/{name}-{version}.tar.gz",
        "strip_prefix": "{name}-{version}",
    },

    "rules_foreign_cc": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_foreign_cc",
        "version": "0.11.1",
        "sha256": "4b33d62cf109bcccf286b30ed7121129cc34cf4f4ed9d8a11f38d9108f40ba74",
        "url": "https://github.com/{repo}/releases/download/{version}/{name}-{version}.tar.gz",
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

    "libtool_source": {
        "type": "http_archive",
        "sha256": "f81f5860666b0bc7d84baddefa60d1cb9fa6fceb2398cc3baca6afaa60266675",
        "version": VERSION_LIBTOOL,
        "url": "https://ftp.wayne.edu/gnu/libtool/libtool-{version}.tar.xz",
        "strip_prefix": "libtool-{version}",
        "build_file_content": """filegroup(name = "all", srcs = glob(["**"]), visibility = ["//visibility:public"])""",
    },
}
