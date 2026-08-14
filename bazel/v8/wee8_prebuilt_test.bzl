load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load(":wee8_prebuilt.bzl", "WEE8_DEFAULT_STDLIB", "wee8_archive_filename", "wee8_legacy_archive_filename", "wee8_prebuilt_repo_name", "wee8_sha256")

def _wee8_prebuilt_helpers_test_impl(ctx):
    env = unittest.begin(ctx)

    asserts.equals(
        env,
        "v8-wee8-1.2.3-linux-x86_64.tar.xz",
        wee8_archive_filename("1.2.3", "x86_64"),
    )
    asserts.equals(
        env,
        "v8-wee8-1.2.3-linux-x86_64-libstdcxx.tar.xz",
        wee8_archive_filename("1.2.3", "x86_64", "libstdcxx"),
    )
    asserts.equals(
        env,
        "v8-wee8-1.2.3-linux-aarch64.tar.xz",
        wee8_legacy_archive_filename("1.2.3", "aarch64"),
    )
    asserts.equals(
        env,
        "v8-wee8-1.2.3-linux-aarch64-libstdcxx.tar.xz",
        wee8_archive_filename("1.2.3", "aarch64", "libstdcxx"),
    )
    asserts.equals(env, "wee8_prebuilt_x86_64", wee8_prebuilt_repo_name("x86_64"))
    asserts.equals(env, "wee8_prebuilt_x86_64_libstdcxx", wee8_prebuilt_repo_name("x86_64", "libstdcxx"))
    asserts.equals(env, "wee8_prebuilt_aarch64", wee8_prebuilt_repo_name("aarch64"))
    asserts.equals(
        env,
        "abc",
        wee8_sha256(
            {
                "wee8_sha256": {
                    "x86_64": {
                        WEE8_DEFAULT_STDLIB: "abc",
                        "libstdcxx": "def",
                    },
                },
            },
            "x86_64",
        ),
    )
    asserts.equals(
        env,
        "def",
        wee8_sha256(
            {
                "wee8_sha256": {
                    "x86_64": {
                        WEE8_DEFAULT_STDLIB: "abc",
                        "libstdcxx": "def",
                    },
                },
            },
            "x86_64",
            "libstdcxx",
        ),
    )
    asserts.equals(
        env,
        "legacy",
        wee8_sha256(
            {
                "wee8_sha256": {
                    "x86_64": "legacy",
                },
            },
            "x86_64",
        ),
    )
    asserts.equals(
        env,
        "",
        wee8_sha256(
            {
                "wee8_sha256": {
                    "aarch64": {
                        WEE8_DEFAULT_STDLIB: "ghi",
                        "libstdcxx": "",
                    },
                },
            },
            "aarch64",
            "libstdcxx",
        ),
    )

    return unittest.end(env)

wee8_prebuilt_helpers_test = unittest.make(_wee8_prebuilt_helpers_test_impl)
