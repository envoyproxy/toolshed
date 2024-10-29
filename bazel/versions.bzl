
VERSIONS = {
    "python": "3.12",

    "bazel_skylib": {
        "type": "github_archive",
        "repo": "bazelbuild/bazel-skylib",
        "version": "1.4.2",
        "sha256": "66ffd9315665bfaafc96b52278f57c7e2dd09f5ede279ea6d39b2be471e7e3aa",
        "url": "https://github.com/{repo}/releases/download/{version}/bazel-skylib-{version}.tar.gz",
    },

    "rules_python": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_python",
        "version": "0.37.2",
        "sha256": "c6fb25d0ba0246f6d5bd820dd0b2e66b339ccc510242fd4956b9a639b548d113",
        "url": "https://github.com/{repo}/releases/download/{version}/{name}-{version}.tar.gz",
        "strip_prefix": "{name}-{version}",
    },
}
