
VERSIONS = {
    "python": "3.11",

    "bazel_skylib": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_python",
        "version": "1.4.2",
        "sha256": "66ffd9315665bfaafc96b52278f57c7e2dd09f5ede279ea6d39b2be471e7e3aa",
        "url": "https://github.com/{repo}/releases/download/bazel-skylib-{version}.tar.gz",
        "strip_prefix": "{name}-{version}",
    },

    "rules_python": {
        "type": "github_archive",
        "repo": "bazelbuild/rules_python",
        "version": "ae9f24ff7cd208af1b895c7509762caaf3b651e0",
        "sha256": "2a5cf996de8d5f6b736005b09a31f774242dd7506bcc1a5ec256946a825d175c",
        "url": "https://github.com/{repo}/archive/{version}.tar.gz",
        "strip_prefix": "{name}-{version}",
    },
}
