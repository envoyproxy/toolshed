# Investigation: per-entry changelog layout (toolshed#4498)

## Summary

Envoy's `changelogs/current.yaml` accumulates all pending entries in a single file, causing constant merge conflicts on active branches. The agreed fix is to split entries into individual RST files at `changelogs/current/<section>/<area>__<slug>.rst`, with a slim `changelogs/current.yaml` retained only to hold the release `date:` field. This document plans the toolshed and Envoy changes needed to support that layout **without breaking the existing release pipeline or stable release branches that still use the old monolithic `current.yaml`**.

### Backward-compatibility principle

Every code path that reads or writes the current changelog **MUST detect the layout at runtime** and dispatch accordingly:

- **"entries" layout** — `changelogs/current/` directory exists. Use the per-entry reader and write the slim `current.yaml`.
- **"yaml" layout** — `changelogs/current/` directory does NOT exist. Use the existing full-YAML reader/writer (current behaviour).

Detection is a single `is_dir()` check against `<project_path>/changelogs/current`. This guarantees:

- Stable release branches (`release/v1.xx`) cut before the migration continue to work without changes.
- Cherry-picks and patch releases on legacy branches keep building.
- Toolshed wheels can be upgraded on legacy branches without breakage.
- A single toolshed version supports both layouts indefinitely.

---

## Toolshed changes

### PR 1 — Typing: decouple `ChangelogSourceDict` / `ChangelogChangeSectionsDict` from hardcoded section keys

- **Files:** [`py/envoy.base.utils/envoy/base/utils/typing.py`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.base.utils/envoy/base/utils/typing.py)
  - Lines 34–43: `ChangelogSourceDict` — hardcoded section keys (`changes`, `behavior_changes`, …)
  - Lines 45–54: `ChangelogChangeSectionsDict` — same set of hardcoded keys
  - Comment on line 35 even says: `# This should match envoy:changelogs/sections.yaml`
- **Description:** The two TypedDicts `ChangelogSourceDict` and `ChangelogChangeSectionsDict` hard-code the seven current section names. With per-entry files, sections are just directory names validated at runtime against `sections.yaml`. Relax both to allow arbitrary string keys (e.g. plain `Dict[str, …]` aliases), and drop or rephrase the misleading comment.
- **Depends on:** Nothing.
- **Risk:** Low. Only typing changes; mypy will catch regressions. `ChangelogSourceDict` is used in `AChangelog.get_data()` (line 135 of `changelog.py`) — the cast target changes but the parsed values are unchanged. **Backward compatible** by construction (relaxed type is a superset of the old type).

---

### PR 2 — Core aggregator: add per-entry RST directory reader in `AChangelog`

- **Files:** [`py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py)
  - Lines 27–34: module-level constants
  - Lines 133–149: `AChangelog.get_data()` classmethod — current YAML reader
  - Lines 163–168: `AChangelog.data` async property — dispatches to `get_data`
- **Description:** Add three new module-level constants:
  ```
  CHANGELOG_CURRENT_DIR_PATH = "changelogs/current"
  CHANGELOG_ENTRY_GLOB = "*/*.rst"
  ENTRY_SEPARATOR = "__"
  ```
  Add a new classmethod `AChangelog.get_data_from_entries(cls, yaml_path, entry_dir) -> ChangelogDict` that: (1) reads `date:` from `yaml_path` (the slim `current.yaml`), (2) walks `entry_dir` for `<section>/<area>__<slug>.rst` files, (3) validates exactly one `__` in the stem, (4) groups entries by section with stable ordering, (5) returns a `ChangelogDict`. Pure addition — `get_data()` and the `data` property are NOT modified in this PR.
- **Depends on:** PR 1 (relaxed TypedDict keys).
- **Risk:** Medium. This is the core parsing path. The validation logic (section names, `__` separator) is new and must exactly match what Envoy will enforce when contributors create entry files. **Backward compatible** because the new method is additive and not yet wired into any caller.

---

### PR 3 — Aggregator: layout-dispatching `write_version` / `write_current` / `write_date` / `changes_for_commit` (+ `get_data` / `data`)

- **Files:** [`py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py)
  - Lines 133–149: `AChangelog.get_data()` — needs to dispatch on layout
  - Lines 163–168: `AChangelog.data` — calls `get_data`, no direct change but inherits dispatch
  - Lines 250–254: `AChangelogs.is_pending` — reads `release_date` from `current` changelog
  - Lines 311–321: `AChangelogs.changes_for_commit()` — returns `CHANGELOG_CURRENT_PATH` on release/dev
  - Lines 385–392: `AChangelogs.write_current()` — creates new blank `current.yaml` from template
  - Lines 394–400: `AChangelogs.write_date()` — writes date into `current.yaml`
  - Lines 402–407: `AChangelogs.write_version()` — copies `current_path.read_text()` to `<version>.yaml`
- **Description:** Introduce a single layout-detection helper, e.g.:
  ```python
  def _entries_layout(self) -> bool:
      return (self.project_path / CHANGELOG_CURRENT_DIR_PATH).is_dir()
  ```
  Then each touched method dispatches on `_entries_layout()`:

  | Method | Legacy layout (`current/` absent) | Entries layout (`current/` present) |
  |---|---|---|
  | `get_data` / `data` | unchanged YAML reader | call `get_data_from_entries(yaml_path, entry_dir)` |
  | `write_version` | unchanged: `version_file.write_text(current_path.read_text())` | aggregate via `get_data_from_entries`, dump YAML to `<version>.yaml`, then remove the `current/` directory |
  | `write_current` | unchanged: write full YAML template | write slim `current.yaml` (`date: Pending`) **and** create empty `current/` directory |
  | `write_date` | unchanged: read full `current.yaml`, merge date, rewrite | read/merge/write the slim `current.yaml` only |
  | `changes_for_commit` | unchanged: `[CHANGELOG_CURRENT_PATH]` | `[CHANGELOG_CURRENT_PATH] + glob("current/**/*.rst")` |
  | `is_pending` | unchanged: read `release_date` from full YAML | read `release_date` from slim YAML (same loader, same key) |

  The legacy branches of every method are byte-for-byte the existing implementations. Only the entries branches are new.
- **Depends on:** PRs 1 and 2.
- **Risk:** **High — release pipeline.** `write_version()` and `write_current()` drive the `dev`/`release` Bazel targets used in `envoy-release.yml`. Any bug here silently produces a malformed `<version>.yaml`. Mitigation: the layout-dispatch pattern keeps the legacy code path identical to today's behaviour, so every existing test continues to exercise it. Add new tests for the entries branch under a temp project layout. **Both layouts must remain green in CI** — add a parametrised fixture that runs the release/dev path twice (once per layout).

---

### PR 4 — Checker: per-entry file naming and section validation in `envoy.code.check`

- **Files:** [`py/envoy.code.check/envoy/code/check/abstract/changelog.py`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.code.check/envoy/code/check/abstract/changelog.py)
  - Lines 40–58: `AChangelogChangesChecker.check_entry()` — RST content checks per entry
  - Lines 60–73: `AChangelogChangesChecker.check_section()` — section-name validity
  - Lines 99–232: `AChangelogStatus` — orchestrates all version/date/section checks
  - Lines 235–267: `AChangelogCheck` — iterates over all changelogs
- **Description:** Add a new checker method `check_entry_filename(self, path: pathlib.Path) -> str | None` that validates: (1) `path.parent.name` is a valid section key (from `self.sections`); (2) the stem contains exactly one `__`; (3) area and slug are both non-empty; (4) extension is `.rst`. Add a content non-emptiness check (empty / whitespace-only RST → error). Wire both into `AChangelogStatus` / `AChangelogCheck` **gated on `current/` directory existence** so legacy branches without per-entry files are unaffected. The `duplicate_current` check (lines 132–137) continues to work unchanged because the slim `current.yaml` still exists.
- **Depends on:** PRs 1–2.
- **Risk:** Low-medium. Adding checks cannot break existing CI; it can only surface new errors in Envoy's per-entry files. The directory-existence gate guarantees legacy branches remain unaffected.

---

### PR 5 — Tests for all above

- **Files:**
  - `py/envoy.base.utils/tests/test_abstract_project_changelogs.py` (42 KB, currently has ~800+ lines)
  - `py/envoy.code.check/tests/test_abstract_changelog.py` (25 KB)
- **Description:** Add unit tests for `get_data_from_entries()` (valid entries, unknown section, missing `__`, `__` in area/slug), `write_version()` with per-entry directory (checks that `<version>.yaml` is correctly aggregated and `current/` directory removed), `write_current()` recreates the empty directory, `write_date()` writes only date to slim YAML, `changes_for_commit()` returns RST glob in entries mode, and the new `check_entry_filename` / content checks. **Crucially**, every dispatch site added in PR 3 must have parametrised tests covering both the legacy-YAML and entries layouts to lock backward compatibility into CI.
- **Depends on:** PRs 1–4.
- **Risk:** Low.

---

## Envoy changes

### PR 1 — Migrate `changelogs/current.yaml` to per-entry layout

- **Files:**
  - `changelogs/current.yaml` — replaced with slim file containing only `date: Pending`
  - `changelogs/current/` — new directory containing one `.rst` file per entry
  - `changelogs/BUILD` ([link](https://github.com/envoyproxy/envoy/blob/main/changelogs/BUILD))
    - Line 9: `glob(["*.*.*.yaml"]) + ["current.yaml"]` — needs to include `glob(["current/**/*.rst"])`
- **Description:** Replace the full `current.yaml` with a slim file (`date: Pending` only). For each entry in the existing `current.yaml`, write one file `changelogs/current/<section>/<area>__<slug>.rst` with the change text as the file body.
- **Depends on:** Toolshed PRs 1–3 published to PyPI and `@base_pip3//envoy_base_utils` / `@base_pip3//envoy_code_check` updated in Envoy's WORKSPACE/requirements.
- **Risk:** **Critical.** This is the commit that flips `main` to the new layout. Because toolshed PR 3 dispatches on layout existence, the new wheel works on `main` (entries) AND on `release/v1.xx` branches (still YAML). Stable release branches are NOT touched by this PR.

---

### PR 2 — Update `changelogs/BUILD` filegroup for CI and docs

- **Files:** `changelogs/BUILD` ([link](https://github.com/envoyproxy/envoy/blob/main/changelogs/BUILD))
  - Line 9: `filegroup("changelogs")` currently uses `glob(["*.*.*.yaml"]) + ["current.yaml"]`
- **Description:** In the `changelogs` filegroup, add `glob(["current/**/*.rst"])`. The `summary` genrule is independent. Bazel targets that depend on `:changelogs` (e.g. `tools/code/BUILD:check`) will pick up the per-entry files.
- **Depends on:** Toolshed PR 4 (checker update) published.
- **Risk:** Low (purely additive Bazel change).

---

### PR 3 — Update CONTRIBUTING.md / maintainer/RELEASE.md for new workflow

- **Files:**
  - `maintainer/RELEASE.md` ([link](https://github.com/envoyproxy/envoy/blob/main/maintainer/RELEASE.md)) — describes `bazel run @envoy_repo//:release` and `dev` in detail (lines 1–200+)
  - `CONTRIBUTING.md` ([link](https://github.com/envoyproxy/envoy/blob/main/CONTRIBUTING.md)) — instructs contributors to edit `changelogs/current.yaml`
  - `PULL_REQUESTS.md` — similar guidance
- **Description:** Update contributor guidance: replace "add an entry to `changelogs/current.yaml`" with "create a file `changelogs/current/<section>/<area>__<slug>.rst`". Document the naming rules (`__` separator, no `__` in area/slug, valid section keys). Add a note about cherry-picks across the layout boundary: backports from `main` (entries) to a `release/v1.xx` branch (legacy YAML) require manually translating the `.rst` file into a YAML entry.
- **Depends on:** Toolshed PR 3 (so the Bazel commands actually work as documented).
- **Risk:** Low (docs only).

---

### PR 4 — `envoy-release.yml` — verify no changes needed; add smoke-test step

- **Files:** `.github/workflows/envoy-release.yml` ([link](https://github.com/envoyproxy/envoy/blob/main/.github/workflows/envoy-release.yml))
  - The `create_release` job runs `bazel run @envoy_repo//:release` (uses toolshed `AChangelogs.write_date()`)
  - The `reopen-branch` job runs `bazel run @envoy_repo//:dev` (uses toolshed `AChangelogs.write_version()` + `write_current()`)
- **Description:** The workflow itself likely needs no YAML changes, since `release` and `dev` Bazel targets are just wrappers around the toolshed Python code. However, add a smoke-test step (e.g. `bazel run @envoy_repo//:dev` in dry-run mode) that asserts the per-entry directory was correctly recreated and the slim `current.yaml` written.
- **Depends on:** Toolshed PR 4 (checker).
- **Risk:** Medium. Any regression here means the release bot fails to create a release commit or creates a malformed one. Should be tested end-to-end in a staging fork first.

---

## Suggested landing order

1. **Toolshed PR 1** — relax TypedDict typing (no behaviour change, safe to merge first)
2. **Toolshed PR 2** — per-entry directory reader (pure addition, backward compatible; not yet wired in)
3. **Toolshed PR 5** (tests) — land alongside or immediately after PR 2/3
4. **Toolshed PR 3** — layout-dispatching `write_version` / `write_current` / `write_date` / `changes_for_commit` / `get_data` (release pipeline impact — needs thorough review and parametrised tests across both layouts)
5. **Toolshed PR 4** — per-entry filename checker (gated on directory existence)
6. *(Toolshed publishes new wheel versions — `envoy.base.utils` and `envoy.code.check`)*
7. **Envoy PR 1** — migrate `current.yaml` content to `current/` directory; update BUILD (depends on new wheel being in WORKSPACE)
8. **Envoy PR 2** — BUILD filegroup addition (can merge same PR as Envoy PR 1 or separately)
9. **Envoy PR 3** — docs update (incl. cherry-pick guidance)
10. **Envoy PR 4** — smoke-test step in `envoy-release.yml`

PRs 1, 2, and 4 in toolshed can be developed in parallel. PR 3 must wait for PR 2 (same file, depends on its API).

---

## Resolved questions

- **`changelogs/current.yaml` on historical branches:** **Resolved.** Toolshed PR 3 dispatches on `(project_path / "changelogs/current").is_dir()`. Legacy `release/v1.xx` branches without that directory continue to use the existing full-YAML reader and writers byte-for-byte. A single toolshed wheel supports both layouts indefinitely.

- **`AChangelogs.is_pending` check (lines 250–254 of `changelog.py`):** **Resolved.** It reads `release_date` from whatever `get_data` returns. With layout-dispatching `get_data` (PR 3), the slim `current.yaml`'s `date: Pending` flows through naturally on entries-layout branches, and the full YAML on legacy branches. No special-casing needed inside `is_pending`.

- **`duplicate_current` check in `AChangelogStatus` (line 132–137 of `envoy.code.check/abstract/changelog.py`):** **Resolved.** The slim `current.yaml` continues to exist alongside the entries directory, so `self.project.changelogs.changelog_path(self.version).exists()` keeps returning the correct value in both layouts. No change needed.

## Open questions

- **Date sentinel design:** Should the slim `changelogs/current.yaml` (containing only `date: Pending`) be kept during development, or should the date be stored in a dedicated file inside `current/` (e.g. `current/_meta.yaml`)? This plan assumes the slim `current.yaml` is retained because it minimises diff with today's release pipeline (`write_date` keeps a near-identical implementation) and keeps backward-compatibility detection trivial.

- **`write_date()` + `write_version()` sequencing:** Currently `release` calls `write_date` (stamps date in `current.yaml`) and `dev` calls `write_version` (copies that stamped file to `<version>.yaml` and rewrites `current.yaml`). In the entries layout, `write_version` must aggregate all entry files into `<version>.yaml` *and then* delete the `current/` directory. The order matters if `write_date` and `write_version` are ever called in the same Bazel invocation — confirm the existing workflow only calls them sequentially across separate jobs.

- **`changes_for_commit()` with many entry files:** The current `AProject._git_commit()` passes all changed paths to `git add` and `git commit` on a single command line. With potentially dozens of `.rst` files, the command line could grow large. Practically this is fine (well under any platform limit), but worth a sanity check on Windows runners if Envoy uses any.

- **Bazel cache invalidation:** Per-entry `.rst` files become Bazel inputs via `changelogs/BUILD`'s `filegroup`. If a contributor adds a new entry file between two `bazel run` invocations, Bazel must correctly invalidate the affected actions. The `glob` pattern handles this in modern Bazel, but worth verifying with a manual test.
