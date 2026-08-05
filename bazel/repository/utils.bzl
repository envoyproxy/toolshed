"""Repository rule for defining a host platform based on CPU architecture.

This allows you to set a single alias for multiple architectures, that resolve
to arch-specific targets. Using `native.alias` and `select` for this doesn't work
when using an arch as the selector.

This can be useful specifically for setting the `host_platform`.

Example usage:

In WORKSPACE:

```starlark
arch_alias(
    name = "clang_platform",
    aliases = {
        "amd64": "@envoy//bazel/platforms/rbe:rbe_linux_x64_clang_platform",
        "aarch64": "@envoy//bazel/platforms/rbe:rbe_linux_arm64_clang_platform",
    },
)
```
And then in .bazelrc:

```
common:clang-common --host_platform=@clang_platform
```

"""

ERROR_UNSUPPORTED = """
Unsupported host architecture '{arch}'. Supported architectures are: {supported}
"""

ALIAS_BUILD = """
alias(
    name = "{name}",
    actual = "{actual}",
    visibility = ["//visibility:public"],
)
"""

def _alias_name(name):
    """Extract the appropriate alias name from the repository context.

    In bzlmod, repository names include the canonical name in any separator
    style (e.g., "+ext+name", "module+ext+name", "module++ext++name", or the
    older "module~~ext~~name" / "module~ext~name"), but we want the alias
    target to use just the apparent name (the final segment, e.g., "name").
    In WORKSPACE mode, the repository name is already the apparent name and
    is returned unchanged.

    Args:
        name: The repository name (ctx.name)

    Returns:
        The apparent name to use for the alias target
    """

    # WORKSPACE mode: the repository name is already the apparent name.
    if "+" not in name and "~" not in name:
        return name

    # bzlmod canonical name in any separator style
    # (e.g. "+ext+name", "module+ext+name", "module++ext++name",
    # or the older "module~~ext~~name" / "module~ext~name"); the
    # apparent name is the final segment.
    return name.replace("~", "+").split("+")[-1]

# Publicly exported for unit testing. Prefer the private `_alias_name`
# internally; this alias only exists so tests can import the logic.
alias_name = _alias_name

def _arch_alias_impl(ctx):
    arch = ctx.os.arch
    actual = ctx.attr.aliases.get(arch)
    if not actual:
        fail(ERROR_UNSUPPORTED.format(
            arch = arch,
            supported = ctx.attr.aliases.keys(),
        ))
    ctx.file(
        "BUILD.bazel",
        ALIAS_BUILD.format(
            name = _alias_name(ctx.name),
            actual = actual,
        ),
    )

arch_alias = repository_rule(
    implementation = _arch_alias_impl,
    attrs = {
        "aliases": attr.string_dict(
            doc = "A dictionary of arch strings, mapped to associated aliases",
        ),
    },
)
