
## Envoy toolshed

<img src="https://github.com/envoyproxy/toolshed/raw/2f3ada749e0d8052b3be2705ac808ed649fcf7e1/envoy-pytooling.png" width="100" align="left" />

Multi-language tooling and libraries for Envoy proxy's CI and development workflows

[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/envoyproxy/toolshed/badge)](https://securityscorecards.dev/viewer/?uri=github.com/envoyproxy/toolshed)

<br clear="both" />

### Contents

- **[actions/](actions/)** - GitHub Actions workflows
- **[bazel/](bazel/)** - Bazel build configurations and rules
- **[js/](js/)** - JavaScript/TypeScript packages
- **[jq/](jq/)** - Assorted jq modules and utilities
- **[py/](py/)** - Python packages, libraries, runners, checkers, and dependencies
- **[rust/](rust/)** - Rust tooling and libraries
- **[sh/](sh/)** - Shell scripts and utilities

### Development

See [DEVELOPER.md](DEVELOPER.md) for information on building, testing, and contributing to the toolshed.

### Build images

Build images published as `docker.io/envoyproxy/envoy-build:<tag>` are also mirrored to
`ghcr.io/envoyproxy/envoy-build:<tag>` with identical tags and architectures.
The `toolshed-echo` image is likewise available from both registries.
See [.github/docker-manifests.yml](.github/docker-manifests.yml) for the published variants,
including the worker and gcc images also published to `gcr.io/envoy-ci`.
