# Hermetic git prebuilt (`//git`)

Builds Linux `git-<version>-<platform>.tar.zst` release artifacts matching the
`bins-v*` packaging flow used for `sq`.

## Runtime layout

Each tarball contains:

- `bin/git`
- `libexec/git-core/git-remote-http`
- `libexec/git-core/git-remote-https`
- `share/git-core/templates/**`

## Runtime environment

The upstream BCR `git` overlay currently builds with `RUNTIME_PREFIX='false'`,
so the packaged `bin/git` does not discover its relocated helper/template paths
automatically.

Consumers must currently set:

```bash
export GIT_EXEC_PATH=/path/to/git-<version>-<platform>/libexec/git-core
export GIT_TEMPLATE_DIR=/path/to/git-<version>-<platform>/share/git-core/templates
```

or wrap `bin/git` to provide those variables.

> TODO: add macOS-ARM64 packaging when the bins pipeline grows beyond Linux
> parity with `sq`.
