# Dependencies workflow

The `Dependencies` workflow is a single-module maintenance workflow for this repository's `/bazel`
workspace.

It supports three actions:

- `report` generates a dependency report artifact and job summary.
- `update-registry` updates the pinned `bazel-registry` SHA and regenerates the lockfile.
- `update-module` updates one `bazel_dep` entry, then regenerates the lockfile.

Use the `dry-run` input to exercise the update flows without opening a pull request.

`update-registry` accepts two additional dispatch inputs:

- `registry-sha`: optional explicit 40-hex commit to pin instead of resolving the current default target.
- `allow-unsafe`: bypass ancestor verification when pinning or checking the registry SHA.

The Bazel updaters only rewrite `bazel/.bazelrc` or `bazel/MODULE.bazel`; lockfile regeneration happens in
this workflow after the updater runs. The workflow now reads registry status from
`bazel run //dependency:update_registry.check`, so PR metadata includes the pinned
SHA, matching tags, and how far the pin is behind `main`.
