VERSIONS = {
    "cmake": "3.23.2",
    "llvm": "18.1.8",
    "ninja": "1.12.0",
    "python": "3.12",
    "bins_release": "0.1.36",
    "msan_libs_sha256": "534e5e6893f177f891d78d6e85a80c680c84f0abd64681f8ddbf2f5457e97a52",
    "tsan_libs_sha256": "2cd571a07014972ff9bc0f189c5725c2ea121aeab0daa4c27ef171842ea13985",

    # Glint binary hashes by architecture
    "glint_sha256": {
        "amd64": "be13b076d0b1ee52d4058549ed10378d757fd481877fdf3d64a5ae86b8808df0",
        "arm64": "a0b9a651e3dee55763a8b8d13f21fbe99e62ffc5ca61a002c0267df4543e53a8",
    },

    # Sysroot hashes organized by glibc version, stdlib variant, and architecture
    # Format: sysroot_hashes[glibc_version][stdlib_variant][arch]
    # stdlib_variant is either "base" (no libstdc++) or the libstdc++ version (e.g., "13")
    "sysroot_hashes": {
        "2.31": {
            "base": {
                "amd64": "7e8c55d3dcf71b27e80dabdf8513f6c26a80d4c53dfe944a0aff6b8528e8f431",
                "arm64": "c7ca2aa531e9aaf8c924146f02eab676718ce83b3be54d7e5e54705d5ccb65b8",
            },
            "13": {
                "amd64": "cc4b09e5b80390179f70532badb3bf4e1f7b06b3cd0f07df8c0c5044e641dcd0",
                "arm64": "da021b4525cf8e2c53b1a090b60a94f3cdfae86ccf8c98c0f65757fdd35e641b",
            },
        },
        "2.28": {
            "base": {
                "amd64": "b1b0f1b496c0be960ab7ea4fa70ae38828bfb1d5dd5bdd68ba569999414cf76b",
                "arm64": "df5fc35de196043bf6355731935194c237bebbdda1cd4c3b4b319cb74befac10",
            },
            "13": {
                "amd64": "234fa9b842e357bc79f5f36a327e6ba5135a9f0c80bf8700151a5e4041b6b69e",
                "arm64": "b6b6474052a5cf3b1e86d6f1a28e4a9105e590b3f4d37ed4590c4aa1f35bc95d",
            },
        },
    },
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
    "rules_pkg": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_pkg",
        "version": "1.2.0",
        "sha256": "b5c9184a23bb0bcff241981fd9d9e2a97638a1374c9953bb1808836ce711f990",
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
        "repo": "bazel-contrib/toolchains_llvm",
        "version": "1.4.0",
        "sha256": "fded02569617d24551a0ad09c0750dc53a3097237157b828a245681f0ae739f8",
        "url": "https://github.com/{repo}/releases/download/v{version}/{name}-v{version}.tar.gz",
        "strip_prefix": "{name}-v{version}",
    },
}
