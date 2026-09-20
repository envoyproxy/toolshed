# Hermetic git prebuilt (`//git`)

Builds Linux `git-<version>-<platform>.tar.zst` release artifacts for the
`bins-v*` flow and exposes a `//git:toolchain_type` consumers can resolve with
no flags or `select()`.

## Runtime layout

Each tarball contains:

- `BUILD.bazel` (`0644`)
- `bin/git` (`0755`)
- `libexec/git-core/git` (`0755`)
- `libexec/git-core/git-remote-http` (`0755`)
- `libexec/git-core/git-remote-https` (symlink to `git-remote-http`)
- `share/git-core/ca-certificates.crt` (`0644`)
- `share/git-core/templates/description` (`0644`)
- `share/git-core/templates/info/exclude` (`0644`)
- `share/git-core/templates/hooks/*.sample` (`0755`)

`bin/git` is self-contained: extract the tarball and run it directly.

The template tree is intentionally pruned to the files `git init` should copy
into new repositories. Source-tree build files such as `Makefile`,
`meson.build`, and `.gitignore` are excluded from the packaged runtime.

## Runtime environment

The upstream BCR `git` overlay currently builds with `RUNTIME_PREFIX='false'`,
so both the prebuilt runtime and the source fallback wrapper set:

- `GIT_EXEC_PATH=$here/libexec/git-core`
- `GIT_TEMPLATE_DIR=$here/share/git-core/templates`
- `GIT_SSL_CAINFO`, with precedence:
  1. explicit `GIT_SSL_CAINFO`
  2. `TOOLSHED_CA_BUNDLE`
  3. bundled `share/git-core/ca-certificates.crt`
- `SSL_CERT_FILE=$GIT_SSL_CAINFO`

## Consuming the toolchain

Registering `@envoy_toolshed//git:toolchain_type` resolves a prebuilt git on
exec platforms with a published `git-<version>-<platform>.tar.zst`
(`linux-x86_64`, `linux-aarch64` today). Other exec platforms fall back to the
source-built `@git//:git` wrapped to match the same runtime contract.

For `genrule`/`sh_*` consumers, declare the toolchain and use `$(GIT)`:

```starlark
genrule(
    name = "git_version",
    outs = ["git-version.txt"],
    cmd = "$(GIT) --version > $@",
    toolchains = ["@envoy_toolshed//git:toolchain_type"],
)
```

For Starlark rules, load `GitInfo` and read `ctx.toolchains`:

```starlark
load("@envoy_toolshed//git:defs.bzl", "GIT_TOOLCHAIN_TYPE", "GitInfo")

my_rule = rule(
    implementation = _impl,
    toolchains = [GIT_TOOLCHAIN_TYPE],
)

# In _impl(ctx):
# git_info = ctx.toolchains[GIT_TOOLCHAIN_TYPE].git  # GitInfo
```

The source fallback can be forced for debugging with:

```console
bazel test //git/test:toolchain_source_version_test   --extra_toolchains=@envoy_toolshed//git:source_toolchain
```

Prebuilt SHAs can be overridden, or a platform disabled, in `MODULE.bazel`:

```starlark
git_prebuilt_ext = use_extension("@envoy_toolshed//git:extensions.bzl", "git_prebuilt_extension")
git_prebuilt_ext.setup(linux_x86_64_sha256 = "...")
# Disable a platform entirely:
# git_prebuilt_ext.setup(linux_aarch64_sha256 = "")
```

## CA bundle maintenance

The bundled CA file is Mozilla's CA bundle published via curl.se and pinned in
`VERSIONS["cacert"]` in `bazel/versions.bzl`. When bumping it:

1. Check the latest dated release on <https://curl.se/docs/caextract.html>.
2. Download `https://curl.se/ca/cacert-YYYY-MM-DD.pem`.
3. Compute its SHA-256.
4. Update `VERSIONS["cacert"]`; the git module extension will recreate
   `@cacert` from that metadata for both packaging and toolchain consumers.
