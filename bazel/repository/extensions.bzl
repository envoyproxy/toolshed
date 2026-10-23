"""Module extension for architecture-specific repository aliases."""

load(":utils.bzl", "arch_alias")

def _arch_alias_ext_impl(module_ctx):
    seen = {}
    for module in module_ctx.modules:
        for tag in module.tags.alias:
            aliases = {}
            if tag.amd64:
                aliases["amd64"] = str(tag.amd64)
            if tag.aarch64:
                aliases["aarch64"] = str(tag.aarch64)
            if not aliases:
                fail("arch_alias '%s' must set at least one of amd64/aarch64" % tag.name)
            if tag.name in seen:
                if seen[tag.name][1] != aliases:
                    fail("arch_alias '%s' declared with conflicting targets by modules %s and %s" % (tag.name, seen[tag.name][0], module.name))
                continue
            seen[tag.name] = (module.name, aliases)
            arch_alias(name = tag.name, aliases = aliases)

_alias = tag_class(attrs = {
    "name": attr.string(mandatory = True, doc = "Apparent repo name of the alias repo."),
    # attr.label resolves against the calling module's repo mapping, so
    # "//bazel/platforms/rbe:linux_x64" from envoy canonicalises correctly.
    "amd64": attr.label(doc = "Target to alias on amd64 hosts."),
    "aarch64": attr.label(doc = "Target to alias on aarch64 hosts."),
})

arch_alias_extension = module_extension(
    implementation = _arch_alias_ext_impl,
    tag_classes = {"alias": _alias},
)
