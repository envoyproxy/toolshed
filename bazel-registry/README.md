# Bazel Registry - Envoy Modules

This directory contains Bazel modules with `.envoy` suffixed versions for use in the Envoy proxy project. The goal is to upstream these modules to their source repositories and eventually to the Bazel Central Registry (BCR).

## Upstreaming Philosophy

**Goal**: Minimize envoy-specific patches by upstreaming to source repos first.

| Type | Example | Approach |
|------|---------|----------|
| **Bazel support** | `MODULE.bazel`, `BUILD.bazel` | Add as first-class build option |
| **Bug fixes** | Null pointer checks, compiler compat | Generic fix, not envoy-specific |
| **Configurability** | Feature flags, build options | Make configurable, not hardcoded |
| **Platform support** | Cross-compile, toolchain fixes | Benefit all users |

### What to Avoid

- ❌ Hardcoding envoy-specific paths (e.g., `@envoy//bazel:foo`)
- ❌ Patches that only work for envoy's build setup
- ❌ Forking when configuration would suffice

### Good vs Bad Example

**Bad (hardcoded):**
```starlark
deps = ["@envoy//bazel:boringcrypto"]
```

**Good (configurable):**
```starlark
deps = select({
    ":use_system_crypto": [],
    "//conditions:default": ["@boringssl//:crypto"],
})
```

## Upstreaming Workflow

```
┌─────────────────────────────────────────────────────────┐
│  1. UPSTREAM TO SOURCE REPO                             │
│     - MODULE.bazel / BUILD.bazel                        │
│     - Generic bug fixes                                 │
│     - Configurable options (not hardcoded)              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  2. UPSTREAM TO BCR                                     │
│     - Once source has clean Bazel support               │
│     - Submit module to Bazel Central Registry           │
│     - Include overlays only if source can't change      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  3. SWITCH ENVOY TO BCR                                 │
│     - Update envoy's MODULE.bazel to use BCR version    │
│     - Toolshed module retained (.envoy version)         │
└─────────────────────────────────────────────────────────┘
```

## Version Naming

All modules use `.envoy` suffix (e.g., `1.2.3.envoy`) to disambiguate from upstream versions. These versions are immutable once created.

## Upstreaming Scenarios

| Scenario | Action |
|----------|--------|
| BCR has exact version | Use BCR directly in envoy |
| BCR exists, needs patches | PR patches to BCR or source, add toolshed mod until landed |
| BCR missing, source has MODULE.bazel | PR to BCR to add module |
| BCR missing, source needs MODULE.bazel | PR to source repo first, then BCR |

## Module Structure

```
modules/
└── <module-name>/
    ├── metadata.json
    └── <version>.envoy/
        ├── MODULE.bazel
        ├── source.json
        ├── presubmit.yml
        ├── patches/          # if needed
        │   └── <module>.patch
        └── overlay/          # if needed
            ├── MODULE.bazel
            └── BUILD.bazel
```

## Tracking Issues

- Open an issue using the ["Upstream Module to BCR" template](../.github/ISSUE_TEMPLATE/upstream-module.yml)
- Link to parent tracking issue: [#3524](https://github.com/envoyproxy/toolshed/issues/3524)
- One issue per `module@version`

## Checklist for New Modules

Before adding a new module:

- [ ] Check [BCR](https://registry.bazel.build/) for existing module/version
- [ ] Check source repo for MODULE.bazel support
- [ ] Create module with `.envoy` version suffix
- [ ] Open tracking issue using the template
- [ ] Plan upstreaming path (source → BCR → envoy switch)

## References

- Parent tracking issue: https://github.com/envoyproxy/toolshed/issues/3524
- Bazel Central Registry: https://registry.bazel.build/
- BCR contribution guide: https://github.com/bazelbuild/bazel-central-registry
