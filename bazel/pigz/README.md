# Hermetic pigz (`//pigz`)

[pigz](https://zlib.net/pigz/), a parallel gzip, exposed as `//pigz:toolchain_type` and, resolved
for the platform it runs on, as the executable target `//pigz`.

## Runtime layout

Each `bins-v*` release publishes `pigz-<version>-linux-{x86_64,aarch64}.tar.zst`:

- `BUILD.bazel`
- `bin/pigz`: the `pigz` module, with zlib-ng (zlib-compatible, for faster compression at the
  same level and format) in place of zlib, and zopfli, linked statically; built against
  toolshed's glibc 2.31 sysroot and stripped.
- `share/doc/`: pigz, zlib-ng and zopfli licenses.

## Consuming pigz

Create the repositories and register the toolchains in the `WORKSPACE`:

```starlark
load("@envoy_toolshed//pigz:repositories.bzl", "load_pigz_toolchains", "setup_pigz")

setup_pigz()

load_pigz_toolchains()
```

Then use `//pigz` as a tool, eg to compress a `pkg_tar` with all the cores:

```starlark
pkg_tar(
    name = "layer",
    srcs = [...],
    compressor = "@envoy_toolshed//pigz",
    # No name or time in the gzip header, for reproducible output.
    compressor_args = "-n",
    extension = "tar.gz",
)
```

As a tool (`cfg = "exec"`), `//pigz` is resolved for the platform the action runs on: the
toolchains match on `target_compatible_with`, which in the exec configuration is that platform.

`//pigz` resolves, in order:

1. a source toolchain, if the consumer registers one before `load_pigz_toolchains()`;
2. the prebuilt for the platform (Linux x86_64 and aarch64, once a bins release publishes them);
3. otherwise, it fails, naming the reason: toolshed does not build pigz for consumers, so that
   they never fetch and compile it unless they ask to.

To build pigz from source where there is no prebuilt, register a toolchain for it, constrained to
where it should build, before `load_pigz_toolchains()`:

```starlark
# tools/pigz/BUILD
load("@envoy_toolshed//pigz:defs.bzl", "PIGZ_TOOLCHAIN_TYPE", "pigz_toolchain")

pigz_toolchain(
    name = "source_impl",
    pigz = "@pigz",
)

toolchain(
    name = "source_toolchain",
    target_compatible_with = ["@platforms//os:macos"],
    toolchain = ":source_impl",
    toolchain_type = PIGZ_TOOLCHAIN_TYPE,
)
```

## Versions

The prebuilts are built and published from `main` (`//pigz/source`), not from this branch. The
release preparation sets `VERSIONS["pigz_sha256"]` from the bins release, enabling the prebuilt
toolchains: until then there is no pigz, so `//pigz` and the tests that run it are `manual`.
Keep `VERSIONS["pigz"]` in sync with the version that `main` publishes.
