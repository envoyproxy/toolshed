# lcov-merge Bazel integration

Repository rule and module extension for the prebuilt `lcov-merge` binary
(`rust/lcov`), a parallel merger for lcov tracefiles used by
`coverage_report` to merge the per-test reports before grcov renders them.

```starlark
lcov_merge = use_extension("@envoy_toolshed//coverage/lcov:extensions.bzl", "lcov_merge_extension")
lcov_merge.setup(bins_release_version = "<bins release>")
use_repo(lcov_merge, "lcov_merge")
```

The binary is `@lcov_merge//:lcov_merge` (or the file `@lcov_merge//:lcov-merge`);
see `//coverage:README.md` for wiring it into a report. Binaries are built for
Linux amd64 and arm64 by the Rust CI and published with the `bins-v*` releases;
their hashes live in `versions.bzl` (`lcov_merge_sha256`). On other platforms the
repository holds a stub that explains itself if run, and `coverage_report` does not
use the merger there, so the fetch never fails.
