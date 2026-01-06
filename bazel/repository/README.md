# Repository Utils

This directory contains utility functions and rules for Bazel repository management.

## arch_alias

`arch_alias` is a repository rule that creates architecture-specific platform aliases. This is useful for setting platform-specific build configurations based on the host CPU architecture.

### Problem Statement

When building software that needs to target different platforms based on the host architecture, you need a way to create aliases that resolve to different platform targets. Using `native.alias` with `select()` doesn't work well when the host architecture is the selector.

### Solution

The `arch_alias` repository rule detects the host CPU architecture at repository loading time and creates an alias that points to the appropriate platform target.

### Usage

#### WORKSPACE Mode (Legacy)

```starlark
load("@envoy_toolshed//bazel/repository:utils.bzl", "arch_alias")

arch_alias(
    name = "clang_platform",
    aliases = {
        "amd64": "@envoy//bazel/platforms/rbe:rbe_linux_x64_clang_platform",
        "aarch64": "@envoy//bazel/platforms/rbe:rbe_linux_arm64_clang_platform",
    },
)
```

#### MODULE.bazel Mode (Bzlmod - Recommended)

```starlark
# In MODULE.bazel
arch_alias_ext = use_extension("@envoy_toolshed//bazel/repository:utils.bzl", "arch_alias_ext")
arch_alias_ext.alias(
    name = "clang_platform",
    aliases = {
        "amd64": "@envoy//bazel/platforms/rbe:rbe_linux_x64_clang_platform",
        "aarch64": "@envoy//bazel/platforms/rbe:rbe_linux_arm64_clang_platform",
    },
)
use_repo(arch_alias_ext, "clang_platform")
```

#### Using in .bazelrc

After defining the alias, you can reference it in your `.bazelrc`:

```
common:clang-common --host_platform=@clang_platform
```

### How It Works

1. The repository rule executes during the loading phase
2. It detects the host CPU architecture using `ctx.os.arch`
3. It looks up the corresponding platform target in the `aliases` dictionary
4. It creates a BUILD file with an `alias()` target pointing to the selected platform
5. The alias can then be referenced as `@<name>` in build configurations

### Supported Architectures

The implementation uses `ctx.os.arch` which returns architecture strings like:
- `amd64` - x86-64 / x64
- `aarch64` - ARM64
- Other architectures as reported by the host OS

### Bzlmod Best Practices

This implementation follows bzlmod best practices:

1. **Module Extension**: Uses `module_extension()` for bzlmod compatibility
2. **Tag Classes**: Defines structured configuration with `tag_class()`
3. **Backward Compatibility**: The repository rule still works in WORKSPACE mode
4. **Repository Declaration**: Repositories are created through the extension, not directly

### Migration from WORKSPACE to Bzlmod

If you're migrating from WORKSPACE to bzlmod:

1. Remove the `arch_alias()` call from your WORKSPACE file
2. Add the equivalent configuration to your MODULE.bazel using the extension
3. Ensure you call `use_repo()` to make the repository visible
4. Update your `.bazelrc` if the repository name changed (though it shouldn't need to)

### Example: Envoy Platform Configuration

In Envoy, this is used to select between different RBE (Remote Build Execution) platforms:

```starlark
arch_alias_ext.alias(
    name = "clang_platform",
    aliases = {
        "amd64": "@envoy//bazel/platforms/rbe:rbe_linux_x64_clang_platform",
        "aarch64": "@envoy//bazel/platforms/rbe:rbe_linux_arm64_clang_platform",
    },
)
```

Then in `.bazelrc`:
```
common:clang-common --host_platform=@clang_platform
```

This allows developers on different architectures to use the same bazel configuration while automatically selecting the appropriate platform.
