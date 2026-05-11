# Investigation: per-entry changelog layout (toolshed#4498)

## Summary

Envoy's `changelogs/current.yaml` accumulates all pending entries in a single file, causing constant merge conflicts on active branches. The agreed fix is to split entries into individual RST files at `changelogs/current/<section>/<area>__<slug>.rst`, where `<section>` is a key from `changelogs/sections.yaml`, `<area>` and `<slug>` are free text that must not contain `__`. The aggregator (in toolshed's `envoy.base.utils.abstract.project.changelog`) must reconstruct the existing `{date, section: [{area, change}, ...]}` in-memory structure so all downstream consumers (docs builds, changelog checks, release machinery) see no change at their interface. The release step (`dev` command, which runs after `release`) must squash the per-entry files into a versioned `<version>.yaml` matching the current historical format, then delete the per-entry directory. Both toolshed and Envoy need coordinated changes; the release pipeline touches at least six places across both repos and must not regress.

---

## Toolshed changes

### PR 1 — Typing: decouple `ChangelogSourceDict` / `ChangelogChangeSectionsDict` from hardcoded section keys

- **Files:** [`py/envoy.base.utils/envoy/base/utils/typing.py`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.base.utils/envoy/base/utils/typing.py)
  - Lines 34–43: `ChangelogSourceDict` — hardcoded section keys (`changes`, `behavior_changes`, …)
  - Lines 45–54: `ChangelogChangeSectionsDict` — same set of hardcoded keys
  - Comment on line 35 even says: `# This should match envoy:changelogs/sections.yaml`
- **Description:** The two TypedDicts `ChangelogSourceDict` and `ChangelogChangeSectionsDict` hard-code the seven current section names. With per-entry files, sections are just directory names validated against `sections.yaml` at parse time, so the TypedDicts no longer need to enumerate them. Replace both dicts with a typed alias using `dict[str, SourceChangeList | None]` / `dict[str, ChangeList | None]` (total=False semantics preserved). Update `BaseChangelogDict` to compose cleanly. Adjust `ChangelogDict` accordingly. No behaviour change — existing YAML parsing downstream still works because the parsed keys are the same strings.
- **Depends on:** Nothing.
- **Risk:** Low. Only typing changes; mypy will catch regressions. `ChangelogSourceDict` is used in `AChangelog.get_data()` (line 135 of `changelog.py`) — the cast target changes but the parsed value is the same. Tests in `test_abstract_project_changelogs.py` reference `typing.ChangelogSourceDict` and will need updating.

---

### PR 2 — Core aggregator: add per-entry RST directory reader in `AChangelog`

- **Files:** [`py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py)
  - Lines 27–34: module-level constants
  - Lines 133–149: `AChangelog.get_data()` classmethod — current YAML reader
  - Lines 163–168: `AChangelog.data` async property — dispatches to `get_data`
- **Description:** Add two new module-level constants:
  ```
  CHANGELOG_CURRENT_DIR_PATH = "changelogs/current"
  CHANGELOG_ENTRY_GLOB = "*/*.rst"
  ENTRY_SEPARATOR = "__"
  ```
  Add a new classmethod `AChangelog.get_data_from_entries(cls, yaml_path, entry_dir) -> ChangelogDict` that: (1) reads `date:` from `yaml_path` (the slim `current.yaml` that still holds `date: Pending`); (2) globs `entry_dir.glob("*/*.rst")`; (3) for each file, validates that `file.parent.name` is a recognised section (compared against `sections.yaml` sections, which the caller must supply), that the file stem contains `__`, and that neither part contains `__`; (4) assembles the `ChangelogDict`. Modify `AChangelog.data` to detect when the companion directory exists (i.e. `self.path.parent / self.path.stem` is a directory) and dispatch to `get_data_from_entries` instead of `get_data`. This keeps backward compatibility: historical `*.*.*.yaml` and any current-layout repo using the old single-file format still work unchanged.
- **Depends on:** PR 1 (relaxed TypedDict keys).
- **Risk:** Medium. This is the core parsing path. The validation logic (section names, `__` separator) is new and must exactly match what Envoy will enforce when contributors create entry files. A mismatch causes silent wrong data or noisy parse errors. The `sections` dict needs to be available to the classmethod — threading it in (from the `AChangelogs` owner) is cleaner than re-reading `sections.yaml` per-entry-file.

---

### PR 3 — Aggregator: update `write_version`, `write_current`, `write_date`, `changes_for_commit`

- **Files:** [`py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py)
  - Lines 311–321: `AChangelogs.changes_for_commit()` — returns `CHANGELOG_CURRENT_PATH` on release/dev
  - Lines 385–392: `AChangelogs.write_current()` — creates new blank `current.yaml` from template
  - Lines 394–400: `AChangelogs.write_date()` — writes date into `current.yaml`
  - Lines 402–407: `AChangelogs.write_version()` — copies `current_path.read_text()` to `<version>.yaml`
- **Description:** Four methods need updating for the new layout:
  1. **`write_version()`** (line 402): currently does `version_file.write_text(current_path.read_text())`. With per-entry files, it must instead: await the aggregated `ChangelogDict` (calling `get_data_from_entries`), call `dump_yaml(data)`, write that to `<version>.yaml`, then delete the entire `changelogs/current/` directory (`shutil.rmtree`). The slim `current.yaml` is left in place for `write_current()` to overwrite next.
  2. **`write_current()`** (line 385): currently writes a full YAML template. With new format, must also create (or recreate) the `changelogs/current/` directory (empty), and write only `date: Pending` to `current.yaml` (not the full section scaffold).
  3. **`write_date()`** (line 394): currently reads all data from `current.yaml`, merges date, rewrites. With per-entry format, `current.yaml` only holds `date:`, so reading/updating that slim file is simpler. If the directory exists, `data` is aggregated, date updated, written back to the full `current.yaml` (this is what `release` writes as the stamped date — then `dev`/`write_version` squashes that into `<version>.yaml`). Actually: `write_date` runs at `release` time and `write_version` at `dev` time. It may be cleaner to make `write_date` write the date-stamped aggregated YAML directly to `<version>.yaml` so `write_version` just does a rename. **Design choice to resolve.**
  4. **`changes_for_commit()`** (line 311): currently adds `CHANGELOG_CURRENT_PATH`. When the new layout is active and a `dev` operation runs, `changed` must include all `changelogs/current/**/*.rst` files plus `changelogs/current.yaml` (for the deletion/reset). Use `glob()` on the current dir to enumerate.
- **Depends on:** PRs 1 and 2.
- **Risk:** **High — release pipeline.** `write_version()` and `write_current()` drive the `dev`/`release` Bazel targets used in `envoy-release.yml`. Any bug here silently produces a malformed `<version>.yaml` (wrong sections, missing entries, wrong date). This must be accompanied by integration-level tests that exercise the full release/dev cycle against a fixture repo. The git commit step (in `AProject._git_commit()`) is passed the file list from `changes_for_commit()`; if the per-entry `.rst` files are not included, they will not be staged for deletion and the directory will persist.

---

### PR 4 — Checker: per-entry file naming and section validation in `envoy.code.check`

- **Files:** [`py/envoy.code.check/envoy/code/check/abstract/changelog.py`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.code.check/envoy/code/check/abstract/changelog.py)
  - Lines 40–58: `AChangelogChangesChecker.check_entry()` — RST content checks per entry
  - Lines 60–73: `AChangelogChangesChecker.check_section()` — section-name validity
  - Lines 99–232: `AChangelogStatus` — orchestrates all version/date/section checks
  - Lines 235–267: `AChangelogCheck` — iterates over all changelogs
- **Description:** Add a new checker method `check_entry_filename(self, path: pathlib.Path) -> str | None` that validates: (1) `path.parent.name` is a valid section key (from `self.sections`); (2) `path.stem` contains exactly one `__`; (3) neither the area part nor the slug part contains `__`. Add a new `AChangelogStatus` method `check_current_entries()` that, when the per-entry directory is present, globs all RST files and runs `check_entry_filename` + existing RST content checks on each. Wire this into `AChangelogStatus.errors` at line 143. The existing `check_sections()` path (which validates the in-memory `ChangelogDict`) continues to work for historical YAML files.
- **Depends on:** PRs 1–2.
- **Risk:** Low-medium. Adding checks cannot break existing CI; it can only surface new errors in Envoy's per-entry files. Must be careful that the checker runs on the current changelog in dev mode (pending) and does not fail when entry files are present but date is `Pending` (that is correct behaviour for dev).

---

### PR 5 — Tests for all above

- **Files:**
  - `py/envoy.base.utils/tests/test_abstract_project_changelogs.py` (42 KB, currently has ~800+ lines)
  - `py/envoy.code.check/tests/test_abstract_changelog.py` (25 KB)
- **Description:** Add unit tests for `get_data_from_entries()` (valid entries, unknown section, missing `__`, `__` in area/slug), `write_version()` with per-entry directory (checks that `<version>.yaml` is correct, that `current/` is deleted, that `changes_for_commit()` returns all entry paths), `write_current()` creates the directory, and all new checker methods. Must also update existing tests that patch `CHANGELOG_CURRENT_PATH` or `write_version`/`write_current` where their internal behaviour changes.
- **Depends on:** PRs 1–4.
- **Risk:** Low.

---

## Envoy changes

### PR 1 — Migrate `changelogs/current.yaml` to per-entry layout

- **Files:**
  - `changelogs/current.yaml` — monolithic file to be replaced
  - `changelogs/current/` — new directory to create with one `.rst` file per entry
  - `changelogs/BUILD` ([link](https://github.com/envoyproxy/envoy/blob/main/changelogs/BUILD))
    - Line 9: `glob(["*.*.*.yaml"]) + ["current.yaml"]` — needs to include `glob(["current/**/*.rst"])`
- **Description:** Create `changelogs/current/` directory. For each entry in the existing `current.yaml`, write one file `changelogs/current/<section>/<area>__<slug>.rst` with the change text as the file content (raw RST, no YAML). Delete `changelogs/current.yaml`'s body, leaving only `date: Pending` (the slim sentinel needed by toolshed's `write_date()` / `write_version()` until the release commits). Update the Bazel `filegroup("changelogs")` in `changelogs/BUILD` to also include `glob(["current/**/*.rst"]) + ["current.yaml"]` (current.yaml remains as a date sentinel). Add a `glob(["current/**/*.rst"])` `filegroup` for any build rules that only need current entries.
- **Depends on:** Toolshed PRs 1–3 published to PyPI and `@base_pip3//envoy_base_utils` / `@base_pip3//envoy_code_check` updated in Envoy's WORKSPACE/requirements.
- **Risk:** **Critical.** This is the commit that removes `current.yaml` content. If toolshed is not updated first and the Bazel `@envoy_repo//:release` and `@envoy_repo//:dev` targets still call the old code, the next release will produce an empty `<version>.yaml`. Must be gated behind the toolshed PRs being published.

---

### PR 2 — Update `changelogs/BUILD` filegroup for CI and docs

- **Files:** `changelogs/BUILD` ([link](https://github.com/envoyproxy/envoy/blob/main/changelogs/BUILD))
  - Line 9: `filegroup("changelogs")` currently uses `glob(["*.*.*.yaml"]) + ["current.yaml"]`
- **Description:** In the `changelogs` filegroup, add `glob(["current/**/*.rst"])`. The `summary` genrule is independent. Bazel targets that depend on `:changelogs` (e.g. `tools/code/BUILD:check`) will automatically pick up the new files. Note that `tools/code/BUILD` runs `envoy.code.check` (line 14: `"changelog"` in `CODE_CHECKS`), so the checker from toolshed PR 4 will run against per-entry files once the wheel is updated.
- **Depends on:** Toolshed PR 4 (checker update) published.
- **Risk:** Low (purely additive Bazel change).

---

### PR 3 — Update CONTRIBUTING.md / maintainer/RELEASE.md for new workflow

- **Files:**
  - `maintainer/RELEASE.md` ([link](https://github.com/envoyproxy/envoy/blob/main/maintainer/RELEASE.md)) — describes `bazel run @envoy_repo//:release` and `dev` in detail (lines 1–200+)
  - `CONTRIBUTING.md` ([link](https://github.com/envoyproxy/envoy/blob/main/CONTRIBUTING.md)) — instructs contributors to edit `changelogs/current.yaml`
  - `PULL_REQUESTS.md` — similar guidance
- **Description:** Update contributor guidance: replace "add an entry to `changelogs/current.yaml`" with "create a file `changelogs/current/<section>/<area>__<slug>.rst`". Document the naming rules (`__` separator, no `__` in area or slug). Update `RELEASE.md` to describe that the `dev` command aggregates all `.rst` files under `current/` into the versioned YAML and then resets the directory; the `release` command just stamps the date (unchanged).
- **Depends on:** Toolshed PR 3 (so the Bazel commands actually work as documented).
- **Risk:** Low (docs only).

---

### PR 4 — `envoy-release.yml` — verify no changes needed; add smoke-test step

- **Files:** `.github/workflows/envoy-release.yml` ([link](https://github.com/envoyproxy/envoy/blob/main/.github/workflows/envoy-release.yml))
  - The `create_release` job runs `bazel run @envoy_repo//:release` (uses toolshed `AChangelogs.write_date()`)
  - The `reopen-branch` job runs `bazel run @envoy_repo//:dev` (uses toolshed `AChangelogs.write_version()` + `write_current()`)
- **Description:** The workflow itself likely needs no YAML changes, since `release` and `dev` Bazel targets are just wrappers around the toolshed Python code. However, add a smoke-test step (e.g. `bazel run @envoy_repo//:changelogs_check -- --dry-run`) before the main run to verify that all per-entry files are valid (correct section dirs, correct filename format). This prevents a malformed entry file from silently producing a bad `<version>.yaml`. Also verify the `check changelog` step runs (via `tools/code/BUILD:check_test`) in the PR CI path so contributors get fast feedback on bad filenames.
- **Depends on:** Toolshed PR 4 (checker).
- **Risk:** Medium. Any regression here means the release bot fails to create a release commit or creates a malformed one. Should be tested end-to-end in a staging fork first.

---

## Suggested landing order

1. **Toolshed PR 1** — relax TypedDict typing (no behaviour change, safe to merge first)
2. **Toolshed PR 2** — per-entry directory reader (pure addition, backward compatible; feature-flagged by directory existence)
3. **Toolshed PR 5** (tests) — land alongside or immediately after PR 2/3
4. **Toolshed PR 3** — `write_version` / `write_current` / `write_date` / `changes_for_commit` updates (release pipeline impact — needs thorough review and integration test)
5. **Toolshed PR 4** — per-entry filename checker
6. *(Toolshed publishes new wheel versions — `envoy.base.utils` and `envoy.code.check`)*
7. **Envoy PR 1** — migrate `current.yaml` content to `current/` directory; update BUILD (depends on new wheel being in WORKSPACE)
8. **Envoy PR 2** — BUILD filegroup addition (can merge same PR as Envoy PR 1 or separately)
9. **Envoy PR 3** — docs update
10. **Envoy PR 4** — smoke-test step in `envoy-release.yml`

---

## Open questions

- **Date sentinel design:** Should the slim `changelogs/current.yaml` (containing only `date: Pending`) be kept during development, or should the date be stored in a dedicated file inside `current/` (e.g. `current/_date.txt`)? The slim-YAML approach requires fewer changes to `write_date()` but could confuse contributors who see a nearly-empty `current.yaml`.

- **`write_date()` + `write_version()` sequencing:** Currently `release` calls `write_date` (stamps date in `current.yaml`) and `dev` calls `write_version` (copies that stamped file to `<version>.yaml`). With per-entry files, should squashing happen at `release` time (producing `<version>.yaml` immediately, making `write_version` a no-op) or still at `dev` time? Moving it to `release` is simpler but changes the current invariant that `current.yaml` is always the authoritative file during the release window.

- **`changes_for_commit()` with many entry files:** The current `AProject._git_commit()` passes all changed paths to `git add` and `git commit` on a single command line (`await self._exec("git", "add", *changed)`). With potentially hundreds of `.rst` files, this could hit shell argument-length limits. Should `git add changelogs/current/` (directory) be used instead?

- **`changelogs/current.yaml` on historical branches:** Stable release branches (`release/v1.xx`) that predate this change will still have `current.yaml` in the old full-YAML form. The toolshed code must handle both layouts at the same time. The "directory exists?" detection (PR 2 above) covers this, but needs explicit tests for the mixed case.

- **Bazel cache invalidation:** Per-entry `.rst` files become Bazel inputs via `changelogs/BUILD`'s `filegroup`. If a contributor adds a new entry file between two `bazel run` invocations, Bazel must re-run any downstream `genrule` that depends on `:changelogs`. Verify that `glob(["current/**/*.rst"])` in `changelogs/BUILD` is not cached across incremental builds (Bazel's `glob()` in `BUILD` files is normally not cached, but this should be confirmed).

- **`AChangelogs.is_pending` check:** Line 250–254 of `changelog.py` checks `await self[self.current].release_date == "Pending"`. With per-entry format, `release_date` comes from the slim `current.yaml`. If that file is missing or malformed, this will raise rather than returning `True`. Should there be a fallback?

- **`duplicate_current` check in `AChangelogStatus` (line 132–137 of `envoy.code.check/abstract/changelog.py`):** This checks `self.project.changelogs.changelog_path(self.version).exists()`. With per-entry format, both `changelogs/current.yaml` (slim) and `changelogs/<version>.yaml` could theoretically coexist during a bad state. The checker should also verify that `changelogs/current/` directory does not exist when a `<version>.yaml` file exists for the current version.
