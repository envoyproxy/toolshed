
VERSION_AUTOCONF = "2.72"
VERSION_AUTOMAKE = "1.16.1"
VERSION_LIBTOOL = "2.4.6"
VERSION_M4 = "1.4.19"

VERSIONS = {
    "cmake": "3.23.2",
    "llvm": "18.1.8",
    "ninja": "1.12.0",
    "python": "3.12",
    "libtool": VERSION_LIBTOOL,
    "m4": VERSION_M4,
    "autoconf": VERSION_AUTOCONF,
    "automake": VERSION_AUTOMAKE,

    "bins_release": "0.1.11",
    "msan_libs_sha256": "38a90e3e015f3e762f51e66d6b3306e91916e03e69295f37b408ebaf80e12d05",
    "tsan_libs_sha256": "3c281d4c823634c74bcb83b6db4a75b5c3b4cbb9dee2346d313826d43392bfe7",
    "sysroot_amd64_sha256": "d9e5879125be147d91f6801176c10a98e2355685ced9ad5a047919dcdbfa93e9",
    "sysroot_arm64_sha256": "05d4d1d61182dec169e4eee0fb3713de4dbd229dfbaac0b9a303edc2155ea5b7",
    "autotools_x86_64_sha256": "30ecac0a2d8d6cae12bfd92b81227628045fc501877e63194c0cd25687a13041",
    "autotools_aarch64_sha256": "f0605601b1ca77832d783259808a18c99c063cf40ec77f705dd551c54e90ec01",

    "m4_source": {
        "type": "http_archive",
        "sha256": "63aede5c6d33b6d9b13511cd0be2cac046f2e70fd0a07aa9573a04a82783af96",
        "version": VERSION_M4,
        "url": "https://mirrors.kernel.org/gnu/m4/m4-{version}.tar.xz",
        "strip_prefix": "m4-{version}",
        "patches": ["//compile:m4-sysroot.patch"],
        "patch_args": ["-p1"],
        "build_file_content": """filegroup(name = \"all\", srcs = glob([\"**\"]), visibility = [\"//visibility:public\"])""",
    },

    "autoconf_source": {
        "type": "http_archive",
        "sha256": "ba885c1319578d6c94d46e9b0dceb4014caafe2490e437a0dbca3f270a223f5a",
        "version": VERSION_AUTOCONF,
        "url": "https://mirrors.kernel.org/gnu/autoconf/autoconf-{version}.tar.xz",
        "strip_prefix": "autoconf-{version}",
        "build_file_content": """filegroup(name = \"all\", srcs = glob([\"**\"]), visibility = [\"//visibility:public\"])""",
    },

    "automake_source": {
        "type": "http_archive",
        "sha256": "5d05bb38a23fd3312b10aea93840feec685bdf4a41146e78882848165d3ae921",
        "version": VERSION_AUTOMAKE,
        "url": "https://mirrors.kernel.org/gnu/automake/automake-{version}.tar.xz",
        "strip_prefix": "automake-{version}",
        "build_file_content": """filegroup(name = \"all\", srcs = glob([\"**\"]), visibility = [\"//visibility:public\"])""",
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

    "libtool_source": {
        "type": "http_archive",
        "sha256": "7c87a8c2c8c0fc9cd5019e402bed4292462d00a718a7cd5f11218153bf28b26f",
        "version": VERSION_LIBTOOL,
        "url": "https://mirrors.kernel.org/gnu/libtool/libtool-{version}.tar.xz",
        "strip_prefix": "libtool-{version}",
        "build_file_content": """filegroup(name = "all", srcs = glob(["**"]), visibility = ["//visibility:public"])""",
    },
}
