# `envoy.base.utils` post-hardening audit against Python 3.12+

Audit target: `py/envoy.base.utils/envoy/base/utils/` at `main` SHA `f96c450`
(contains merged PR #4353).

---

## Table of contents

1. [Scope and method](#scope-and-method)
2. [Changes since previous audit](#changes-since-previous-audit)
3. [Module inventory](#module-inventory)
4. [Consumer map](#consumer-map)
5. [Console scripts / entry points](#console-scripts--entry-points)
6. [Cross-cutting findings](#cross-cutting-findings)
7. [Prioritized follow-up plan](#prioritized-follow-up-plan)

---

## Scope and method

I re-read every module under `py/envoy.base.utils/envoy/base/utils/`, then mapped consumers in:

- `envoyproxy/toolshed` under `py/` (excluding `py/envoy.base.utils` itself), using semantic search + repository grep/AST mapping.
- `envoyproxy/envoy`, using GitHub code search (imports, Bazel rules, requirements, and console-script references).

Verdict labels:

- **KEEP**
- **KEEP-BUT-MODERNISE**
- **DEPRECATE**
- **MOVE**
- **DROP**

---

## Changes since previous audit

### Fixed since PR #4340

- ✅ **Resolved (PR #4353): shell-string git execution hardening**
  - `AProject._exec()` now uses `create_subprocess_exec(*command)`.
  - `AProject._git_commit()` now passes argv components directly.
  - Manual shell escaping was removed.
- ✅ `@classmethod @property` breakage risk removed via new `descriptors.classproperty` in `data_env.py` and `jinja_env.py`.
- ✅ `datetime.utcnow()` deprecation fixed (`datetime.now(timezone.utc)` now used).
- ✅ `pytz` dependency removed from UTC formatting helper.
- ✅ `parallel_runner` modernized to `itertools.batched` + `create_subprocess_exec`.
- ✅ YAML global SafeLoader/SafeDumper mutation was removed; dedicated `EnvoyLoader`/`EnvoyDumper` subclasses are now used.

### Previous follow-up items still open

- `to_yaml` remains thin and deprecatable.
- `coverage_with_data_file` is still test-centric and should move out of base utils.
- `LegacyChangelog` retention should still be explicitly re-validated.
- `AProject.__init__(loop=...)` remains vestigial/deprecated-style API baggage.

### New findings in this audit

- New export-surface bug: `__all__` includes `"Parallel"` but no such symbol exists.
- Tar extraction hardening is only partial: selective extraction now uses `filter="data"`, but `extractall()` path still uses default filter behavior.

---

## Module inventory

### `__init__.py` (package export surface)

~89 LOC.

| Symbol(s) | Description | LOC | Verdict |
|---|---:|---:|---|
| Re-exported API (`extract`, `typed`, `Project`, `ProtobufValidator`, runners, commands, etc.) | Public facade for package consumers. | ~89 | **KEEP** |
| `Parallel` (in `__all__` only) | Listed in `__all__` but not defined/imported. | 1 | **DROP** |

### `utils.py`

~169 LOC.

| Symbol | Description | LOC | Verdict |
|---|---|---:|---|
| `coverage_with_data_file` | Temporary `.coveragerc` writer context manager. | ~15 | **MOVE** |
| `from_json`, `from_yaml` | File read + parse helpers with optional typed cast. | ~18 | **KEEP** |
| `to_yaml` | File write wrapper around `yaml.dump`. | ~10 | **DEPRECATE** |
| `ellipsize` | Fixed-width truncation with `...`. | ~6 | **KEEP** |
| `typed` | Runtime structural type check helper (`trycast`). | ~13 | **KEEP** |
| `cd_and_return` | cwd context manager. | ~10 | **DEPRECATE** |
| `is_sha` | 40-char hex SHA validator. | ~8 | **KEEP** |
| `dt_to_utc_isoformat` | UTC date-normalization helper. | ~4 | **KEEP** |
| `last_n_bytes_of` | Tail-bytes file helper. | ~6 | **KEEP** |
| `minor_version_for`, `increment_version` | `packaging.Version` helpers. | ~9 | **KEEP** |
| `TuplePairError`, `tuple_pair` | Strict key/value split helper. | ~9 | **KEEP** |

### `tar.py`

~269 LOC.

| Symbol | Description | LOC | Verdict |
|---|---|---:|---|
| `TAR_EXTS`, `Tar*Mode` aliases | Supported archive extension/mode surface. | ~8 | **KEEP** |
| `ExtractError`, `is_tarlike`, `tar_mode` | Validation and mode helpers. | ~16 | **KEEP** |
| `extract`, `untar`, `pack`, `repack` | Archive operations including `.zst` path. | ~63 | **KEEP** |

Stdlib note: stdlib tar support still does not remove the value of this module while `.zst` compatibility and path remap/filter features are required.

### `yaml.py`

~52 LOC.

| Symbol | Description | LOC | Verdict |
|---|---|---:|---|
| `IgnoredKey` | Envoy `!ignore` YAML tag object. | ~26 | **KEEP** |
| `EnvoyLoader`, `EnvoyDumper` | Dedicated safe loader/dumper subclasses with tag registration. | ~14 | **KEEP** |

### `typing.py`

~119 LOC.

| Symbol group | Description | Verdict |
|---|---|---|
| `Change`, changelog TypedDict family (`SourceChangeDict`, `ChangeDict`, `Changelog*`) | Changelog and section schema contracts. | **KEEP** |
| Project result TypedDicts (`ProjectDevResultDict`, `ProjectReleaseResultDict`, `ProjectSyncResultDict`, `ProjectPublishResultDict`, `ProjectTriggerResultDict`, `ProjectChangeDict`) | Project workflow data contracts. | **KEEP** |
| Mapping aliases (`VersionDict`, `InventoryDict`, `SyncResultDict`, etc.) | Reused typed map aliases. | **KEEP** |

### `exceptions.py`

~41 LOC. `TypeCastingError`, `ChangelogError`, `ChangelogParseError`, `ReleaseError`, `DevError`, `CommitError`, `PublishError`, `ChecksumError`, `SignatureError` are all still live.

**Verdict:** **KEEP**.

### `interface.py`

~451 LOC. Public abstract contracts: `IProtobufSet`, `IProtobufValidator`, `IInventories`, `IChangelogEntry`, `IChangelog`, `IChangelogs`, `IProject`.

**Verdict:** **KEEP**.

### `descriptors.py`

~31 LOC.

| Symbol | Description | LOC | Verdict |
|---|---|---:|---|
| `classproperty` | Replacement for removed `@classmethod`+`@property` stacking. | ~24 | **KEEP** |

### `abstract/project/changelog.py`

~430 LOC.

| Symbol | Description | LOC | Verdict |
|---|---|---:|---|
| `AChangelogEntry`, `AChangelog`, `AChangelogs` | Changelog domain implementation core. | ~321 | **KEEP** |
| `LegacyChangelog` | Parser for pre-1.23 RST changelog format. | ~42 | **KEEP-BUT-MODERNISE** |
| Changelog path/url constants | File/URL templates and section constants. | ~25 | **KEEP** |

### `abstract/project/inventory.py`

~165 LOC.

| Symbol | Description | LOC | Verdict |
|---|---|---:|---|
| `AInventories` | Inventory sync/index/write abstraction. | ~139 | **KEEP** |
| Inventory path/url constants | Location and URL templates. | ~6 | **KEEP** |

### `abstract/project/project.py`

~367 LOC.

| Symbol | Description | LOC | Verdict |
|---|---|---:|---|
| `AProject` | Project lifecycle abstraction (sync/dev/release/publish/trigger/commit). | ~340 | **KEEP** |
| `ENVOY_REPO`, `MAIN_BRANCH`, `VERSION_PATH` | Project defaults/constants. | 3 | **KEEP** |

Post-#4353 status: subprocess hardening work is complete and correct.

### `abstract/protobuf.py` + `protobuf.py`

~98 LOC abstract + ~17 LOC concrete.

| Symbol | Description | Verdict |
|---|---|---|
| `AProtobufSet` / `ProtobufSet` | Descriptor set loading + pool build. | **KEEP** |
| `AProtobufValidator` / `ProtobufValidator` | YAML/JSON config validation against Envoy protos. | **KEEP** |

### `project.py`

~48 LOC concrete wiring (`ChangelogEntry`, `Changelog`, `Changelogs`, `Inventories`, `Project`).

**Verdict:** **KEEP**.

### `data_env.py` + `data_env_cmd.py`

~47 + ~16 LOC.

| Symbol | Description | Verdict |
|---|---|---|
| `DataEnvironment` | Serialize JSON/YAML -> pickle and load back. | **KEEP** |
| `data_env_cmd`/`main` | Console entrypoint wrapper. | **KEEP** |

### `jinja_env.py` + `jinja_env_cmd.py`

~71 + ~16 LOC.

| Symbol | Description | Verdict |
|---|---|---|
| `JinjaEnvironment` | Template precompile/load and custom filter registration. | **KEEP** |
| `jinja_env_cmd`/`main` | Console entrypoint wrapper. | **KEEP** |

### `fetch_runner.py` + `fetch_cmd.py`

~282 + ~16 LOC.

| Symbol | Description | Verdict |
|---|---|---|
| `FetchRunner` | Concurrent downloader + checksum/signature verification + optional pack/extract. | **KEEP** |
| `fetch_cmd`/`main` | Console entrypoint wrapper. | **KEEP** |
| `DEFAULT_CHUNK_SIZE`, `DEFAULT_MAX_CONCURRENCY` | Runtime defaults. | **KEEP** |

### `parallel_runner.py` + `parallel_cmd.py`

~63 + ~16 LOC.

| Symbol | Description | Verdict |
|---|---|---|
| `ParallelRunner` | Batch command executor using `itertools.batched` + async subprocess exec. | **KEEP** |
| `parallel_cmd`/`main` | Console entrypoint wrapper. | **KEEP** |

### `project_runner.py` + `project_cmd.py` + `project_data_cmd.py`

~346 + ~16 + ~16 LOC.

| Symbol | Description | Verdict |
|---|---|---|
| `BaseProjectRunner`, `ProjectRunner`, `ProjectDataRunner` | CLI orchestration for project lifecycle + data output. | **KEEP** |
| `project_cmd`, `project_data_cmd`, `main` wrappers | Console entrypoint wrappers. | **KEEP** |
| Message constants (`NOTIFY_MSGS`, `COMMIT_MSGS`, etc.) | UX templates / defaults. | **KEEP** |

### `abstract/__init__.py` + `abstract/project/__init__.py`

Re-export modules for abstract API (`AProject`, `AChangelog*`, `AInventories`, `AProtobuf*`).

**Verdict:** **KEEP**.

---

## Consumer map

## `envoyproxy/toolshed` (`py/` outside `envoy.base.utils`)

| Consumer package | Symbols consumed |
|---|---|
| `envoy.code.check` | `IProject`, `Project`, `interface`, `typing`, `exceptions`, `last_n_bytes_of`, `typed` |
| `envoy.dependency.check` | `typed`, `from_yaml`, `dt_to_utc_isoformat`, `is_sha` |
| `envoy.distribution.verify` | `from_yaml`, `extract` |
| `envoy.docs.sphinx_runner` | `from_yaml`, `typed`, `to_yaml`, `extract`, `is_tarlike`, `pack`, `ProtobufValidator`, `interface` |
| `envoy.github.release` | `extract`, `is_tarlike` |
| `envoy.gpg.sign` | `tuple_pair`, `repack` |
| `py/tools/fuzzing` | `envoy.base.utils.yaml.EnvoyLoader` |

Low/zero in-repo consumers among exported surface include: `coverage_with_data_file`, `fetch_cmd`, `parallel_cmd`, `ProjectRunner`, `ProjectDataRunner`, `DataEnvironment`, `JinjaEnvironment`, `TAR_EXTS`, `tar_mode`, and most command-wrapper `main` functions.

## `envoyproxy/envoy`

Direct consumers identified by lexical + semantic search:

| File | Usage |
|---|---|
| `docs/tools/generate_version_histories.py` | `from envoy.base import utils`; `from envoy.base.utils import IProject, Project`; `from envoy.base.utils.project import Inventories`; uses `utils.minor_version_for` |
| `docs/tools/generate_extensions_security_rst.py` | `from envoy.base import utils`; uses `utils.from_yaml` |
| `docs/tools/protodoc/manifest_to_json.py` | `from envoy.base.utils import ProtobufValidator` |
| `test/config_test/static_config_validation.py` | `from envoy.base.utils import ProtobufValidator` |
| `tools/api_proto_breaking_change_detector/buf_utils.py` | `from envoy.base.utils import cd_and_return` |
| `tools/api_proto_breaking_change_detector/detector_test.py` | `from envoy.base.utils import cd_and_return` |
| `tools/base/requirements.in` | direct dependency: `envoy.base.utils>=0.5.10` |
| `tools/base/envoy_python.bzl` | console scripts `envoy.jinja_env`, `envoy.data_env`; generated Python imports `envoy.base.utils.jinja_env.JinjaEnvironment` |
| `bazel/repo.bzl` | console scripts `envoy.project`, `envoy.project_data` via `py_console_script_binary` |
| `tools/api_proto_breaking_change_detector/BUILD` | Bazel dep `requirement("envoy.base.utils")` |

No direct in-repo hits for `envoy.fetch` or `envoy.parallel` script names in `envoyproxy/envoy`.

---

## Console scripts / entry points

| Script | Entry point | Observed usage |
|---|---|---|
| `envoy.data_env` | `envoy.base.utils:data_env_cmd` | Active via `tools/base/envoy_python.bzl` |
| `envoy.jinja_env` | `envoy.base.utils:jinja_env_cmd` | Active via `tools/base/envoy_python.bzl` |
| `envoy.project` | `envoy.base.utils:project_cmd` | Active via `bazel/repo.bzl` |
| `envoy.project_data` | `envoy.base.utils:project_data_cmd` | Active via `bazel/repo.bzl` |
| `envoy.fetch` | `envoy.base.utils:fetch_cmd` | No direct repo references found |
| `envoy.parallel` | `envoy.base.utils:parallel_cmd` | No direct repo references found |

---

## Cross-cutting findings

1. **Resolved hardening item (#4353):** `AProject._exec`/`_git_commit` now use argument-vector subprocess execution (`create_subprocess_exec`), removing shell-string quoting fragility.
2. **`tar.py` safety still has one open edge:** selective `tar.extract(..., filter="data")` is fixed, but `extractall()` path still relies on default filter behavior.
3. **`__all__` correctness issue:** package `__all__` still exports `"Parallel"` even though no such symbol exists.
4. **`cd_and_return` is now externally visible in Envoy (`buf_utils.py`, `detector_test.py`)**; any deprecation requires coordinated migrations.
5. **`AProject.__init__(loop=...)` remains legacy API surface** and should be reviewed against modern asyncio usage patterns.
6. **Legacy changelog parser (`LegacyChangelog`) remains in use-capable path** but should be explicitly tied to currently supported release windows.

---

## Prioritized follow-up plan

### P0 / correctness

1. **Harden remaining tar extraction path**
   - Apply explicit safe filter semantics to the `extractall()` branch in `tar.py`.

2. **Fix export-surface inconsistency**
   - Remove `"Parallel"` from `__all__` or add the intended symbol.

### Resolved from previous plan

- ✅ **Old cross-cutting item #7 resolved:** shell-string `_exec` path removed.
- ✅ **Old follow-up item #9 resolved by PR #4353:** `_git_commit` now uses `create_subprocess_exec` argument lists.

### KEEP-BUT-MODERNISE / structural

3. **Plan migration off `cd_and_return`**
   - Migrate Envoy consumers to `contextlib.chdir` (or local helper), then deprecate/remove.

4. **Review/remove vestigial `loop` plumbing in `AProject`**
   - Validate whether `loop` is still needed by directory integrations.

5. **Re-validate need for `LegacyChangelog`**
   - Confirm if any still-supported release data requires the RST parser path.

### DEPRECATE / MOVE

6. **Deprecate `to_yaml`**
   - Replace remaining callsites with direct `path.write_text(yaml.dump(...))`.

7. **Move `coverage_with_data_file` out of `envoy.base.utils`**
   - Relocate to a test-focused utility package.

