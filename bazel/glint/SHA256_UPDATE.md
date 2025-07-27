# Glint Toolchain Setup

## SHA256 Hash Update Instructions

After the first release with glint binaries:

1. Download the binaries from the release:
   ```bash
   wget https://github.com/envoyproxy/toolshed/releases/download/bazel-bins-v0.1.11/glint-0.1.0-amd64
   wget https://github.com/envoyproxy/toolshed/releases/download/bazel-bins-v0.1.11/glint-0.1.0-arm64
   ```

2. Calculate the SHA256 hashes:
   ```bash
   sha256sum glint-0.1.0-amd64
   sha256sum glint-0.1.0-arm64
   ```

3. Update the hashes in `/bazel/versions.bzl`:
   - `glint_amd64_sha256`: Update with the amd64 hash
   - `glint_arm64_sha256`: Update with the arm64 hash

4. Update the `bins_release` version if needed.

## Testing the Toolchain

After updating the hashes:

```bash
cd bazel
bazel test //toolchains/glint/test:glint_toolchain_test
```

## Building from Source (Fallback)

For architectures without prebuilt binaries:

```bash
cd bazel
bazel build //rust/glint:glint_binary
```
