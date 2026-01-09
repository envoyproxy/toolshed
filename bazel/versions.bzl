VERSIONS = {
    "cmake": "3.23.2",
    "llvm": "18.1.8",
    "ninja": "1.12.0",
    "python": "3.12",
    "bins_release": "0.1.35",
    "msan_libs_sha256": "534e5e6893f177f891d78d6e85a80c680c84f0abd64681f8ddbf2f5457e97a52",
    "tsan_libs_sha256": "c8ba1214e7d9f03e6d330a816ef5ce268f8d75c28375ed21f051993828f77dd7",

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
                "amd64": "26827e3e82fc549454dcb5a9d6eba1868fe00f797c3bdfc2146be72b6ac196b9",
                "arm64": "1e8d0b441b5410cc2d7042083f07a92e298f2520dedf99e4f43284c8e362475e",
            },
            "13": {
                "amd64": "37b5946a536cc75a9aff8511914b1b639f59e6e335b21125289d3c50a9a962d4",
                "arm64": "5239abbc8e90f61cfdb5f4a561e2ee06810a99cb923b207eab4e2c847199c8ee",
            },
        },
        "2.28": {
            "base": {
                "amd64": "ecc2706e5a57b882f9e2bd90d91cfe955639bc7ce8080ab62bebb497471a826a",
                "arm64": "80cf6ec9ccd36a72335b65b18d46a86edd83122301a16afdcde965fcf0e4359f",
            },
            "13": {
                "amd64": "532c22c00a21899bee3f11d8c33468f65d4e52b0f5ca5a8cbb4b1081d1438b39",
                "arm64": "21d2d87526ac127144b05de3c7b2b9a6f5b8fed83885a7d90ea9c3ea2d5ca072",
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
        "version": "1.0.1",
        "sha256": "d20c951960ed77cb7b341c2a59488534e494d5ad1d30c4818c736d57772a9fef",
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
