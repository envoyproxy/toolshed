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

LLVM_VERSION = "18.1.8"

VERSIONS = {
    "cmake": "3.23.2",
    "llvm": LLVM_VERSION,
    "ninja": "1.12.0",
    "python": "3.12",
    "bins_release": "0.1.50",
    "msan_libs_sha256": "886114d236bbf5162e09fa7cef71f0f1dbae4a5edfce99dc254ac7d9651389e7",
    "tsan_libs_sha256": "837433f11b9b3354175cb31a62dba18f0ac9733fe156cce89ccda94f687ff4ee",

    "libcxx_libs_sha256": {
        "aarch64": "b4d598c338e7b9f4af38cf09ef52ae5758f69980f68320602b2a214e3d6c944e",
        "x86_64": "d5e95a23e964c521a8fde618eb46de5c7e4c182f544e367e19fe1a9482002dfb",
    },

    # Glint binary hashes by architecture
    "glint_sha256": {
        "amd64": "737c2cce19349f27f875132a51f698007804457eb6c7781f302ca83648d2fc9c",
        "arm64": "47a52a683cb54b7a91b68c31917e73dfe7db483b2f66372fb6da6fe2b098da48",
    },

    # Sysroot hashes organized by glibc version, stdlib variant, and architecture
    # Format: sysroot_hashes[glibc_version][stdlib_variant][arch]
    # stdlib_variant is either "base" (no libstdc++) or the libstdc++ version (e.g., "13")
    "sysroot_hashes": {
        "2.31": {
            "base": {
                "amd64": "3834985da6246da888ce257627138222ed2100967cdb8d96b051b71a5442fcd5",
                "arm64": "06e7a168d94398a3578801e801e12eef33e2661ce5bb4acd5c202e23abfe399a",
            },
            "13": {
                "amd64": "fb1cc19db235e9843bb27adf270912849ed9d87708585163faebec397b65f3ec",
                "arm64": "43f4d409a1a2ef305e06e327b2226f39778f2369d40b0acea20c11dd37ec4983",
            },
        },
        "2.28": {
            "base": {
                "amd64": "5aa3e73f32d16173ffd8d057b4cc14b3df1f409ae07889f56d26d8b607938040",
                "arm64": "d74464bb62bc810331d69a73b66807adbad12170aa321f0f014156afb016db04",
            },
            "13": {
                "amd64": "88f823c482899f771b37b116a4a206037f87056d69adea1bb4fc49055cc39b75",
                "arm64": "7d9d4b000870014fcde9384eed9d1126e5dc053f874af4c8bad2cca8146d0bab",
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
        "version": "1.4.2",
        "sha256": "66ffd9315665bfaafc96b52278f57c7e2dd09f5ede279ea6d39b2be471e7e3aa",
        "url": "https://github.com/{repo}/releases/download/{version}/bazel-skylib-{version}.tar.gz",
    },
    "llvm_libcxx_aarch64": {
        "arch": "aarch64",
        "type": "http_archive",
        "repo": "llvm/llvm-project",
        "download_suffix": "linux-gnu",
        "version": LLVM_VERSION,
        "sha256": "dcaa1bebbfbb86953fdfbdc7f938800229f75ad26c5c9375ef242edad737d999",
        "url": "https://github.com/{repo}/releases/download/llvmorg-{version}/clang+llvm-{version}-{arch}-{download_suffix}.tar.xz",
        "strip_prefix": "clang+llvm-{version}-{arch}-linux-gnu/",
        "build_file_content": LLVM_CXX_BUILD,
    },
    "llvm_libcxx_x86_64": {
        "arch": "x86_64",
        "download_suffix": "linux-gnu-ubuntu-18.04",
        "type": "http_archive",
        "repo": "llvm/llvm-project",
        "version": LLVM_VERSION,
        "sha256": "54ec30358afcc9fb8aa74307db3046f5187f9fb89fb37064cdde906e062ebf36",
        "url": "https://github.com/{repo}/releases/download/llvmorg-{version}/clang+llvm-{version}-{arch}-{download_suffix}.tar.xz",
        "strip_prefix": "clang+llvm-{version}-{arch}-linux-gnu-ubuntu-18.04/",
        "build_file_content": LLVM_CXX_BUILD,
    },
    "llvm_source": {
        "type": "github_archive",
        "repo": "llvm/llvm-project",
        "version": "llvmorg-%s" % LLVM_VERSION,
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
        "version": "1.6.0",
        "sha256": "2b298a1d7ea99679f5edf8af09367363e64cb9fbc46e0b7c1b1ba2b1b1b51058",
        "url": "https://github.com/{repo}/releases/download/v{version}/{name}-v{version}.tar.gz",
        "strip_prefix": "{name}-v{version}",
    },
}
