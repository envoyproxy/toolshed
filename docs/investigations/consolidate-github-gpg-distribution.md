# Investigation: consolidating `envoy.github.*`, `envoy.gpg.*`, and `envoy.distribution.*`

## Scope and sources

This report is based on the current `envoyproxy/toolshed` tree and targeted code search in `envoyproxy/envoy` / `envoyproxy/envoy-website`.

Primary sources in `toolshed`:

- `py/README.md`
- `py/tools/publish_check/BUILD`
- `py/envoy.github.abstract/**`
- `py/envoy.github.release/**`
- `py/envoy.gpg.identity/**`
- `py/envoy.gpg.sign/**`
- `py/envoy.distribution.distrotest/**`
- `py/envoy.distribution.release/**`
- `py/envoy.distribution.repo/**`
- `py/envoy.distribution.verify/**`

Primary sources in `envoy`:

- `tools/base/requirements.in`
- `tools/distribution/BUILD`
- `distribution/BUILD`
- `distribution/packages.bzl`
- `tools/dev/requirements.in`

`envoy-website` code search found no usage of `envoy.github.*`, `envoy.gpg.*`, or `envoy.distribution.*`.

---

## 1) Inventory

### `envoy.github.*`

| Package path under `py/` | PyPI name | Short description | Public entry points / API surface | Internal toolshed deps (notable) | External runtime deps (notable) |
|---|---|---|---|---|---|
| `py/envoy.github.abstract` | `envoy.github.abstract` | “Abstract interfaces for the Github release tool used in Envoy proxy's CI” (`setup.cfg`) | Exported ABCs/types from `envoy/github/abstract/__init__.py`: `AGithubRelease`, `AGithubReleaseManager`, `AGithubReleaseRunner`, `AGithubReleaseCommand`, `AGithubReleaseAssets*`, `ReleaseDict`, `GithubReleaseError` | Used by `envoy.github.release`; used by `envoy.distribution.release`; declared in `envoy.distribution.repo` metadata | `abstracts`, `aio.core`, `aio.run.runner`, `aiohttp`, `gidgethub`, `verboselogs` |
| `py/envoy.github.release` | `envoy.github.release` | “Github release tool used in Envoy proxy's CI” (`setup.cfg`) | Exported concrete classes from `envoy/github/release/__init__.py`: `GithubRelease`, `GithubReleaseManager`, `GithubReleaseAssetsFetcher`, `GithubReleaseAssetsPusher`, `stream` | Depends on `envoy.github.abstract`; consumed by `envoy.distribution.release` (`runner.py` and metadata); declared in `envoy.distribution.repo` metadata | `aiofiles`, `aiohttp`, `gidgethub`, `packaging`, `verboselogs`, `envoy.base.utils` |

### `envoy.gpg.*`

| Package path under `py/` | PyPI name | Short description | Public entry points / API surface | Internal toolshed deps (notable) | External runtime deps (notable) |
|---|---|---|---|---|---|
| `py/envoy.gpg.identity` | `envoy.gpg.identity` | “GPG identity util used in Envoy proxy's CI” (`setup.cfg`) | `GPGIdentity`, `GPGError` via `envoy/gpg/identity/__init__.py` | Consumed by `envoy.gpg.sign` (`runner.py` + metadata) | `python-gnupg`, `aio.core` |
| `py/envoy.gpg.sign` | `envoy.gpg.sign` | “GPG signing util used in Envoy proxy's CI” (`setup.cfg`) | Console script `envoy.gpg.sign` (`setup.cfg` entry_points); API exports include `PackageSigningRunner`, `BinarySigningUtil`, `DebSigningUtil`, `RPMSigningUtil`, `DirectorySigningUtil` | Depends on `envoy.gpg.identity` | `aio.run.runner`, `envoy.base.utils` |

### `envoy.distribution.*`

| Package path under `py/` | PyPI name | Short description | Public entry points / API surface | Internal toolshed deps (notable) | External runtime deps (notable) |
|---|---|---|---|---|---|
| `py/envoy.distribution.distrotest` | `envoy.distribution.distrotest` | “Lib for testing packages with distributions in Envoy proxy's CI” (`setup.cfg`) | Exports `DistroTestConfig`, `DistroTestImage`, `DistroTest` and related exceptions via `__init__.py`; no console script | Consumed by `envoy.distribution.verify` (`checker.py`, metadata) | `aiodocker`, `aio.run.checker`, `envoy.base.utils`, `envoy.docker.utils` |
| `py/envoy.distribution.release` | `envoy.distribution.release` | “Release publishing tool used in Envoy proxy's CI” (`setup.cfg`) | Console script `envoy.distribution.release`; commands registered in `cmd.py`: `list`, `info`, `assets`, `create`, `delete`, `push`, `fetch`; `ReleaseRunner` | Depends on both `envoy.github.abstract` and `envoy.github.release` (metadata + runtime imports) | Primarily cross-toolshed deps, minimal third-party surface in package itself |
| `py/envoy.distribution.repo` | `envoy.distribution.repo` | `setup.cfg` says release publishing tool; README says repo publishing tool | Console script `envoy.distribution.repo`; `RepoBuildingRunner`, `DebRepoManager`, abstract repo interfaces | Metadata declares deps on `envoy.github.abstract` + `envoy.github.release`; current source imports do **not** reference `envoy.github.*` (possible stale metadata coupling) | `abstracts`, `aio.core`, `aio.run.runner`, `envoy.base.utils` |
| `py/envoy.distribution.verify` | `envoy.distribution.verify` | “Package distribution verification tool used in Envoy proxy's CI” (`setup.cfg`) | Console script `envoy.distribution.verify`; `PackagesDistroChecker` | Depends on `envoy.distribution.distrotest` (metadata + runtime import) | `aio.run.checker`, `aiodocker` (through checker), `envoy.base.utils` |

Published-package inventory is also reflected in `py/tools/publish_check/BUILD` and listed in `py/README.md`.

---

## 2) Usage analysis

## Inside `envoyproxy/toolshed`

### Direct code-level coupling (runtime imports)

- `envoy.github.release` imports `envoy.github.abstract` (`py/envoy.github.release/envoy/github/release/{assets.py,manager.py,release.py}`).
- `envoy.distribution.release` imports both `envoy.github.abstract` and `envoy.github.release` (`py/envoy.distribution.release/envoy/distribution/release/{commands.py,runner.py}`).
- `envoy.gpg.sign` imports `envoy.gpg.identity` (`py/envoy.gpg.sign/envoy/gpg/sign/runner.py`).
- `envoy.distribution.verify` imports `envoy.distribution.distrotest` (`py/envoy.distribution.verify/envoy/distribution/verify/checker.py`).

### Packaging-level coupling (install requirements)

- `envoy.github.release` requires `envoy.github.abstract`.
- `envoy.distribution.release` requires `envoy.github.abstract` + `envoy.github.release`.
- `envoy.distribution.repo` requires `envoy.github.abstract` + `envoy.github.release` (metadata only; not evident in source imports).
- `envoy.gpg.sign` requires `envoy.gpg.identity`.
- `envoy.distribution.verify` requires `envoy.distribution.distrotest`.

### Internal infra/CI usage in toolshed

- All 8 packages are tracked in `py/tools/publish_check/BUILD` as publish artefacts.
- All 8 are also pinned in `py/deps/requirements.in` for toolshed’s own Python dependency set.
- No references were found in `actions/` or `.github/` to these package names or their console script names directly; toolshed Actions do not appear to wrap these CLIs.

### Potentially low-usage package inside toolshed

- `envoy.distribution.repo` appears to be used primarily by its own tests in toolshed; no in-repo runtime consumers were found outside its package/tests.

## Inside `envoyproxy/envoy`

### Confirmed consumption

- `tools/base/requirements.in` pins all relevant distribution/gpg/github packages (except `envoy.github.abstract`, which is indirect in some flows):
  - `envoy.distribution.distrotest`
  - `envoy.distribution.release`
  - `envoy.distribution.repo`
  - `envoy.distribution.verify`
  - `envoy.gpg.identity`
  - `envoy.gpg.sign`
  - `envoy.github.release`
- `tools/distribution/BUILD` maps console scripts to Bazel executables:
  - `envoy.distribution.release`
  - `envoy.gpg.sign`
  - `envoy.distribution.verify`
- `distribution/packages.bzl` invokes `//tools/distribution:sign` in genrules.
- `distribution/BUILD` invokes `//tools/distribution:sign` and `//tools/distribution:verify` as part of packaging/signing/verification flows.

### Likely unused (or not found in code search)

- No direct import usage in Python source under `envoy` was found for `envoy.github.*`, `envoy.gpg.*`, `envoy.distribution.*`.
- No code-search hits were found for `envoy.distribution.repo` usage beyond requirement pinning.
- No code-search hits were found for `//tools/distribution:release` invocation, despite the target being defined.

## Inside `envoyproxy/envoy-website`

- No usage found for any of the investigated namespaces.

---

## 3) Cohesion / coupling assessment

### Tight coupling candidates

1. **`envoy.github.abstract` + `envoy.github.release`**
   - The concrete implementation is tightly coupled to the abstract layer.
   - `envoy.distribution.release` depends on both, and its runner is effectively a thin integration layer over them.
   - Maintaining a separate published abstract package increases release choreography and compatibility surface.

2. **`envoy.gpg.identity` + `envoy.gpg.sign`**
   - `envoy.gpg.sign`’s core runner is directly built around `GPGIdentity`.
   - The identity package has very focused utility value but little independent consumption.

3. **`envoy.distribution.distrotest` + `envoy.distribution.verify`**
   - `verify` is a checker wrapper around distrotest configuration/execution.
   - These look like one cohesive “distribution validation” concern split across two distributions.

### Medium/uncertain coupling

4. **`envoy.distribution.release` with github release packages**
   - Strong runtime coupling today (explicit imports).
   - Functionally this is “distribution CLI wrapper over github release primitives.”

5. **`envoy.distribution.repo`**
   - The package is distribution-oriented, but metadata still references github release packages while source imports do not.
   - This suggests historical coupling that may no longer be real, or a stale dependency declaration.

### Abstraction package value (`envoy.github.abstract`)

- Pros: clear contracts for release manager/release/assets/runner/command.
- Cons: additional package/version boundary for an abstraction currently serving mostly one concrete implementation (`envoy.github.release`).
- Current shape indicates the abstraction may no longer “earn its own distribution” even if interfaces remain valuable internally.

### Cross-namespace overlap

- Release publishing workflow spans at least:
  - github release operations (`envoy.github.release`)
  - distribution release command orchestration (`envoy.distribution.release`)
  - package signing (`envoy.gpg.sign`)
  - package verification (`envoy.distribution.verify`/`distrotest`)
- This end-to-end flow is conceptually one release pipeline, but presently split across multiple PyPI package boundaries.

---

## 4) Consolidation options

## Option A: Minimal, low-risk consolidation

- Merge only obvious pairs:
  - fold `envoy.github.abstract` into `envoy.github.release`
  - fold `envoy.gpg.identity` into `envoy.gpg.sign`
  - fold `envoy.distribution.distrotest` into `envoy.distribution.verify`
- Keep `envoy.distribution.release` and `envoy.distribution.repo` as separate distributions.

**Pros**
- Smaller migration.
- Reduces package count quickly.
- Minimal downstream Bazel target churn in `envoy`.

**Cons**
- Leaves substantial fragmentation in distribution/release area.
- Keeps some historical package boundaries that are arguably artificial.

**Breaking-change surface**
- Moderate if old PyPI names are removed immediately; low if old names are retained as compatibility shims.

**PyPI rename/deprecation requirement**
- Yes, if package names are removed.
- Can be softened by republishing old names as thin compatibility distributions.

## Option B: Per-namespace consolidation (recommended)

- Collapse each namespace into one distribution:
  - `envoy.github`
  - `envoy.gpg`
  - `envoy.distribution`
- Keep current module paths (e.g. `envoy/github/release/...`) internally; consolidate only distribution boundaries first.

**Pros**
- Big reduction in release/version management overhead.
- Preserves conceptual namespace boundaries and ownership.
- Easier for downstream `envoy` requirements/Bazel mapping than a cross-namespace redesign.

**Cons**
- Requires coordinated dependency updates in `envoy`.
- Temporary dual-publish period likely needed.

**Breaking-change surface**
- Medium.
- Mostly packaging/import-install expectations; Python import paths can remain stable if modules are preserved.

**PyPI rename/deprecation requirement**
- Yes: old package names should be deprecated and/or converted to shim packages that depend on new consolidated names.

## Option C: Cross-namespace consolidation into release pipeline packages

- Build around end-to-end release concerns (example: `envoy.release` + maybe `envoy.release.verify`).
- Absorb relevant github, gpg, and distribution pieces into workflow-centric packages.

**Pros**
- Highest conceptual cohesion for release pipeline users.
- Could remove deepest historical namespace artifacts.

**Cons**
- Highest migration complexity and risk.
- Largest downstream refactor + communication burden.
- Harder incremental rollout.

**Breaking-change surface**
- High (package names, likely module paths, tool invocation patterns).

**PyPI rename/deprecation requirement**
- Extensive.

---

## 5) Recommendation

Recommend **Option B (per-namespace consolidation)**, with an incremental rollout and compatibility period.

Rationale:

1. It removes most package-boundary overhead while preserving recognizable domains (`github`, `gpg`, `distribution`).
2. It aligns with current coupling patterns already visible in code.
3. It avoids the high disruption of a cross-namespace redesign while still addressing the “too many tiny packages” root issue.

### Suggested migration plan

1. **Prepare consolidated packages without changing imports**
   - Introduce consolidated distributions that include existing module trees.
   - Keep current import paths (`envoy.github.release`, `envoy.gpg.sign`, etc.) intact.

2. **Add compatibility shims for old PyPI names**
   - Republish old package names as minimal distributions depending on the new consolidated package(s).
   - Document deprecation timeline in package metadata/README.

3. **Update `toolshed` internal dependency declarations**
   - Replace inter-package requirements with intra-distribution module deps where possible.
   - Remove stale coupling (notably validate whether `envoy.distribution.repo` still needs github deps).

4. **Update `envoy` in one compatibility-safe step**
   - Adjust `tools/base/requirements.in` to consolidated names.
   - Update Bazel pip repository/package mappings (`tools/distribution/BUILD` package labels).
   - Validate packaging targets that call `sign`/`verify` (`distribution/BUILD`, `distribution/packages.bzl`).

5. **Deprecation phase**
   - Keep shims for 1–2 release cycles.
   - Remove legacy package publications only after downstream consumers are confirmed migrated.

This keeps `envoy` building throughout by avoiding abrupt import-path or CLI-name breaks.

---

## 6) Open questions

1. **Is `envoy.distribution.repo` still used in real release workflows?**
   - It is pinned in `envoy/tools/base/requirements.in`, but no concrete usage was found in code search.

2. **Is `//tools/distribution:release` still actively invoked in CI/release jobs?**
   - Target is defined, but no direct invocation was found in code search.

3. **Should `envoy.github.abstract` remain a first-class abstraction boundary?**
   - If only one concrete implementation is expected long-term, keeping it as a separate published distribution likely adds more cost than value.

4. **Should consolidation stop at package boundaries, or also rationalize CLI contracts?**
   - Current CLIs (`envoy.distribution.release`, `envoy.distribution.verify`, `envoy.gpg.sign`) may be candidates for a unified top-level release CLI in a later phase.

5. **Deprecation policy preference**
   - How long should old PyPI names be supported as shims before removal?

---

## Appendix: quick dependency/coupling map

- `envoy.github.release` -> `envoy.github.abstract`
- `envoy.distribution.release` -> `envoy.github.abstract` + `envoy.github.release`
- `envoy.gpg.sign` -> `envoy.gpg.identity`
- `envoy.distribution.verify` -> `envoy.distribution.distrotest`

These four edges are the strongest immediate consolidation candidates.
