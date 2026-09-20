"""Shared helpers for module extensions."""

def single_setup_tag(module_ctx, ext_name, repos, attrs):
    """Return a single shared setup() tag, rejecting conflicting configs.

    Args:
      module_ctx: Module extension context supplying setup() tags.
      ext_name: Human-readable extension name for conflict messages.
      repos: Repository names included in conflict messages.
      attrs: Setup-tag attrs that must match across modules.

    Returns:
      The shared setup() tag, or None when no module declared one.
    """
    tags = [
        tag
        for mod in module_ctx.modules
        for tag in mod.tags.setup
    ]
    if not tags:
        return None
    chosen = tags[0]
    for tag in tags[1:]:
        for attr_name in attrs:
            if getattr(tag, attr_name) == getattr(chosen, attr_name):
                continue
            fail(
                (("Conflicting setup() calls found for %s. " +
                  "Repository names are fixed to %s, so all modules " +
                  "must request identical configuration " +
                  "(differing attribute: %s).") % (ext_name, repos, attr_name)),
            )
    return chosen
