# `envoy.base.utils` audit against Python 3.12+ stdlib

Audit target: `py/envoy.base.utils/envoy/base/utils/` at `main` SHA
[`47d31e2872cc10ef1ce5f13f82686506f73354fe`](https://github.com/envoyproxy/toolshed/tree/47d31e2872cc10ef1ce5f13f82686506f73354fe/py/envoy.base.utils/envoy/base/utils)

---

## Table of contents

1. [Scope and method](#scope-and-method)
2. [Module inventory](#module-inventory)
   - [utils.py](#utilspy)
   - [tar.py](#tarpy)
   - [yaml.py](#yamlpy)
   - [typing.py](#typingpy)
   - [exceptions.py](#exceptionspy)
   - [interface.py](#interfacepy)
   - [abstract/ — project layer](#abstract--project-layer)
   - [project.py](#projectpy)
   - [protobuf.py / abstract/protobuf.py](#protobufpy--abstractprotobufpy)
   - [data\_env.py / data\_env\_cmd.py](#data_envpy--data_env_cmdpy)
   - [jinja\_env.py / jinja\_env\_cmd.py](#jinja_envpy--jinja_env_cmdpy)
   - [fetch\_runner.py / fetch\_cmd.py](#fetch_runnerpy--fetch_cmdpy)
   - [parallel\_runner.py / parallel\_cmd.py](#parallel_runnerpy--parallel_cmdpy)
   - [project\_runner.py / project\_cmd.py / project\_data\_cmd.py](#project_runnerpy--project_cmdpy--project_data_cmdpy)
3. [Consumer map](#consumer-map)
   - [envoyproxy/toolshed py/](#envoyproxytoolshed-py)
   - [envoyproxy/envoy](#envoyproxyenvoy)
4. [Console scripts / entry points](#console-scripts--entry-points)
5. [Cross-cutting findings](#cross-cutting-findings)
6. [Prioritized follow-up plan](#prioritized-follow-up-plan)

---

## Scope and method

I read every source file under `py/envoy.base.utils/envoy/base/utils/`, mapped all
`from envoy.base import utils` / `from envoy.base.utils import …` / `import envoy.base.utils…`
usages across every other package under `py/` (not `envoy.base.utils` itself, not its
own tests), and searched `envoyproxy/envoy` via GitHub code search for direct Python
imports, Bazel rule usage, and `requirements.in` references.

The verdict column uses exactly these labels:

| Label | Meaning |
|---|---|
| **KEEP** | Stdlib does not cover this (or covers it poorly); helper has real consumers. |
| **KEEP-BUT-MODERNISE** | Still useful, but implementation is dated. |
| **DEPRECATE** | Modern stdlib (3.12+ baseline) does this cleanly; migrate consumers then remove. |
| **MOVE** | Symbol is fine but doesn't belong in `envoy.base.utils`. |
| **DROP** | Zero consumers in either repo and no obvious external value. |

---

## Module inventory

### `utils.py`

~192 LOC. The original "grab-bag" module: small utilities imported throughout
the ecosystem.

| Symbol | Description | LOC | Verdict |
|---|---|---|---|
| `coverage_with_data_file` | Context manager that writes a temporary `.coveragerc` with a custom `data_file` path. | ~15 | **MOVE** |
| `from_json` | Reads a JSON file from `path` and optionally runs it through `typed()`. | ~7 | **KEEP** |
| `from_yaml` | Reads a YAML file from `path` and optionally runs it through `typed()`. | ~7 | **KEEP** |
| `to_yaml` | Dumps data to a YAML file at `path`; returns the path. | ~6 | **DEPRECATE** |
| `ellipsize` | Truncates a string to `max_len` characters, appending `…`. | ~5 | **KEEP** |
| `typed` | Casts a value to a given type/TypedDict using `trycast.isassignable`; raises `TypeCastingError` on failure. | ~8 | **KEEP** |
| `async_list` | Drains an `AsyncGenerator` into a list, with optional predicate filter. | ~8 | **DEPRECATE** |
| `cd_and_return` | `chdir` context manager: changes to `path` and restores previous cwd on exit. | ~9 | **DEPRECATE** |
| `to_bytes` | Converts `str → bytes` (UTF-8); passes through if already `bytes`. | ~4 | **DEPRECATE** |
| `is_sha` | Checks if a 40-char hex string looks like a git SHA. | ~7 | **KEEP** |
| `dt_to_utc_isoformat` | Converts a `datetime` to a UTC ISO date string (`YYYY-MM-DD`). | ~4 | **KEEP-BUT-MODERNISE** |
| `last_n_bytes_of` | Reads the last `n` bytes from a file using `seek`. | ~6 | **KEEP** |
| `minor_version_for` | Returns a `packaging.Version` with only `major.minor` (zeroes patch). | ~2 | **KEEP** |
| `increment_version` | Returns a new `packaging.Version` with minor or patch incremented. | ~5 | **KEEP** |
| `TuplePairError` | Exception raised when `tuple_pair` splits to anything other than 2. | ~2 | **KEEP** |
| `tuple_pair` | Splits a string on a separator into a strict 2-tuple; raises `TuplePairError` otherwise. | ~7 | **KEEP** |

**Stdlib comparison details**

- `to_yaml` — `pathlib.Path.write_text(yaml.dump(data))` is one line. The helper saves nothing.
- `async_list` — `[x async for x in gen]` / `[x async for x in gen if filter(x)]` does this inline since Python 3.6+.
- `cd_and_return` — `contextlib.chdir` was added in **Python 3.11**. The package's `setup.cfg` specifies `python_requires >= 3.11` (which is also the baseline assumed throughout this audit), so this helper is redundant on every supported interpreter version.
- `to_bytes` — inline `data if isinstance(data, bytes) else data.encode()` is universally understood; the helper pre-dates f-strings and adds import overhead.
- `dt_to_utc_isoformat` — replaces `pytz.UTC` with `datetime.timezone.utc` (stdlib since 3.2). The function itself is still useful as a single-call API, but the internal `pytz` dependency can be eliminated.
- `coverage_with_data_file` — the inline comment already says *"consider moving to tools.testing.utils"*. It is a testing concern, not a general utility.

**Module verdict:** Mostly `KEEP` with a clean set of small deprecations and one move. This module is the workhorse of the package and broadly used — do not hollow it out aggressively.

---

### `tar.py`

~267 LOC. Tar archive helpers with **zstd** support and pattern-based
extraction/packing.

| Symbol | Description | LOC | Verdict |
|---|---|---|---|
| `TAR_EXTS` | `set[str]` of known tarball extensions. | 1 | **KEEP** |
| `TarWriteMode`, `TarReadMode`, `TarMode` | `Literal` type aliases for `tarfile.open` mode strings. | ~6 | **KEEP** |
| `ExtractError` | Raised when no tarballs are provided to `extract()`. | ~2 | **KEEP** |
| `is_tarlike` | Returns `True` if path string ends with a known tar extension. | ~4 | **KEEP** |
| `tar_mode` | Returns the correct `tarfile.open` mode string for a given path. | ~6 | **KEEP** |
| `extract` | Extracts one or more tarballs to a directory; supports pattern matching, path remapping, and zst. | ~15 | **KEEP** |
| `untar` | Context manager that extracts to a `TemporaryDirectory` and cleans up. | ~12 | **KEEP** |
| `pack` | Packs a directory tree to a tar archive (all formats, including `.zst`). | ~4 | **KEEP** |
| `repack` | Context manager: untar into temp dir, yield it for modification, then repack. | ~8 | **KEEP** |

**Stdlib comparison:** `tarfile` in the stdlib handles `.tar`, `.tar.gz`, `.tar.bz2`, `.tar.xz`
but does **not** support `.tar.zst` / `.zst` as of Python 3.12 (zstd support arrives in
CPython's `tarfile` only in 3.14 via [PEP 783](https://peps.python.org/pep-0783/)). The
`zstandard` third-party dependency is therefore genuinely required until the project drops
support for Python < 3.14. Additionally the pattern-matching, prefix-mapping, and in-memory
decompression pipeline in `_open_zst` / `_extract` / `_mv_paths` / `_rm_paths` are
non-trivial enhancements that stdlib doesn't offer.

**Latent bug:** `_extract` calls the deprecated `TarFile.extract(member, path=…)` without the
`filter` parameter (CVE-2007-4559 / tarfile path-traversal mitigations). Python 3.12 emits
`DeprecationWarning` and Python 3.14 will remove the unsafe default. The call should be
updated to `tar.extract(member, path=…, filter="data")` or at minimum `filter="tar"`.

**Note on the old TODO:** The comment `# remove zst when https://bugs.python.org/issue37095 is resolved` refers to the stdlib tarfile zstd proposal. That issue was resolved as accepted (PEP 783) and landed in **Python 3.14** (released April 2025). As of the audit date (May 2026) Python 3.14 is the current release, but dropping the `zstandard` dependency requires the project to raise `python_requires >= 3.14` — a significant version gate that should be a deliberate policy decision. Until that gate is raised, `zstandard` remains a required dependency. The TODO should be updated to note the version gate rather than the upstream issue status.

**Module verdict:** Entirely `KEEP`. The zstd support and pattern extraction are genuinely non-trivial. Fix the `TarFile.extract` deprecation warning.

---

### `yaml.py`

~44 LOC. Envoy-specific YAML tag handling.

| Symbol | Description | LOC | Verdict |
|---|---|---|---|
| `IgnoredKey` | `yaml.YAMLObject` subclass that handles the Envoy `!ignore` YAML tag. | ~25 | **KEEP** |
| `EnvoyYaml` | Class whose cached `yaml` property registers `!ignore` constructors/representers. | ~12 | **KEEP** |
| `envoy_yaml` | Module-level singleton instance of `EnvoyYaml`. | 1 | **KEEP** |

**Stdlib comparison:** Standard `yaml` (`pyyaml`) does not handle `!ignore` out of the box.
The `!ignore` tag is an Envoy-specific extension. No stdlib alternative.

**Design note:** `EnvoyYaml.yaml` mutates `_yaml.SafeLoader` / `_yaml.SafeDumper` as a
side-effect of accessing the property. This is a global mutation of pyyaml's shared
state — calling `envoy_yaml.yaml` in any process permanently affects all `yaml.safe_load`
calls in that process. If this is intentional it should be documented; if not it should be
refactored to use a dedicated `Loader` subclass.

**Module verdict:** `KEEP`. Envoy-specific; no stdlib alternative. Document the global side-effect.

---

### `typing.py`

~115 LOC. Domain `TypedDict` types and type aliases for changelog, inventory, and
project result dictionaries.

| Symbol | Description | Verdict |
|---|---|---|
| `Change` | `str` subclass whose `__add__` returns `Change`. Used to tag changelog text. | **KEEP** |
| `SourceChangeDict` | `TypedDict` — raw YAML changelog entry. | **KEEP** |
| `ChangeDict` | `TypedDict` — parsed changelog entry (with `Change` type). | **KEEP** |
| `ChangeList`, `SourceChangeList` | Type aliases for lists of the above. | **KEEP** |
| `BaseChangelogDict` | `TypedDict` — just `date: str`. | **KEEP** |
| `ChangelogSourceDict` | `TypedDict` — all change sections (from source YAML). | **KEEP** |
| `ChangelogChangeSectionsDict` | `TypedDict` — all change sections (parsed). | **KEEP** |
| `ChangelogDict` | Inherits both above. | **KEEP** |
| `ChangelogPathsDict` | `dict[Version, Path]`. | **KEEP** |
| `ChangelogsDict` | `dict[Version, IChangelog]`. | **KEEP** |
| `MinorVersionsDict` | `dict[Version, tuple[Version, ...]]`. | **KEEP** |
| `BaseChangelogSectionDict` | `TypedDict` — section title. | **KEEP** |
| `ChangelogSectionDict` | `TypedDict` — section title + optional description. | **KEEP** |
| `ChangelogSectionsDict` | `dict[str, ChangelogSectionDict]`. | **KEEP** |
| `VersionConfigDict` | `dict[str, str]` — version config map. | **KEEP** |
| `ProjectDevResultDict` | `dict` — placeholder for dev-operation results. | **KEEP-BUT-MODERNISE** |
| `SyncResultDict` | `dict[Version, bool]`. | **KEEP** |
| `ProjectReleaseResultDict` | `TypedDict` — release date + version string. | **KEEP** |
| `ProjectSyncResultDict` | `TypedDict` — changelog + inventory sync results. | **KEEP** |
| `ProjectPublishResultDict` | `TypedDict` — GitHub release metadata. | **KEEP** |
| `ProjectTriggerResultDict` | `TypedDict` — workflow name. | **KEEP** |
| `ProjectChangeDict` | `TypedDict` — umbrella dict for all change types. | **KEEP** |
| `VersionDict` | `dict[Version, Version]`. | **KEEP** |
| `InventoryDict` | `dict[Version, Path]`. | **KEEP** |

**Type-hint modernization debt:** `typing.TypedDict`, `typing.Iterator`, `typing.ItemsView`,
`typing.ValuesView`, `typing.KeysView` are imported from `typing` — all of these have been
re-exported from `collections.abc` (for container ABCs) or can use the native `type X = …`
syntax on 3.12+. `TypedDict` itself should still come from `typing` (or `typing_extensions`)
but the rest could be cleaned up.

`ProjectDevResultDict = dict` is an untyped alias — it should be a proper `TypedDict`.

**Module verdict:** `KEEP-BUT-MODERNISE`. The types are necessary and Envoy-specific; the
implementation needs a modern `typing` clean-up pass.

---

### `exceptions.py`

~39 LOC. Domain exception hierarchy.

| Symbol | Description | Verdict |
|---|---|---|
| `TypeCastingError(TypeError)` | Raised by `typed()` when `trycast.isassignable` rejects a value. Carries `.value`. | **KEEP** |
| `ChangelogError(Exception)` | Base changelog operational error. | **KEEP** |
| `ChangelogParseError(Exception)` | Raised when a changelog YAML file fails to parse. | **KEEP** |
| `ReleaseError(Exception)` | Raised during release workflow errors. | **KEEP** |
| `DevError(Exception)` | Raised during dev-mode transition errors. | **KEEP** |
| `CommitError(Exception)` | Raised when a git commit subprocess fails. | **KEEP** |
| `PublishError(Exception)` | Raised during GitHub release publishing. | **KEEP** |
| `ChecksumError(Exception)` | Raised when a file checksum doesn't match the expected value. | **KEEP** |
| `SignatureError(Exception)` | Raised when GPG signature validation fails. | **KEEP** |

**Module verdict:** `KEEP`. All exceptions are actively raised and caught by consumers.
The hierarchy is flat; grouping some under a common `BaseProjectError` base would help callers
that want to catch broadly, but that is a separate refactor.

---

### `interface.py`

~452 LOC. Abstract interface definitions using the `abstracts` framework.

| Symbol | Description | Verdict |
|---|---|---|
| `IProtobufSet` | Interface for loading Protobuf descriptor sets. | **KEEP** |
| `IProtobufValidator` | Interface for validating YAML/JSON against Envoy proto3 schemas. | **KEEP** |
| `IInventories` | Interface for managing Sphinx `objects.inv` inventories. | **KEEP** |
| `IChangelogEntry` | Interface for a single changelog entry (area + change text). | **KEEP** |
| `IChangelog` | Interface for one versioned changelog file. | **KEEP** |
| `IChangelogs` | Interface for the full changelog collection. | **KEEP** |
| `IProject` | Top-level interface for Envoy project management (version/changelog/inventory/release/sync). | **KEEP** |

**Stdlib comparison:** None of these have stdlib analogues — they are domain interfaces.

**Type-hint debt:** `interface.py` imports `typing.AsyncGenerator`, `typing.ItemsView`,
`typing.Iterator`, `typing.KeysView`, `typing.ValuesView` from `typing` instead of
`collections.abc`. On Python 3.9+ these can come directly from `collections.abc` (or the
type itself can be written with built-in generics, e.g., `Iterator[X]` → `Iterator[X]`).

**Module verdict:** `KEEP`. Core contract surface; well-structured.

---

### `abstract/` — project layer

Three modules totalling ~530 LOC:

- `abstract/project/changelog.py` (~432 LOC) — `AChangelogEntry`, `AChangelog`,
  `AChangelogs`, plus the internal `LegacyChangelog` RST-era parser.
- `abstract/project/inventory.py` (~166 LOC) — `AInventories`.
- `abstract/project/project.py` (~372 LOC) — `AProject`.
- `abstract/protobuf.py` (~112 LOC) — `AProtobufSet`, `AProtobufValidator`.

| Symbol | Description | Verdict |
|---|---|---|
| `AChangelogEntry` | Abstract changelog entry (area + change); implements `IChangelogEntry`. | **KEEP** |
| `LegacyChangelog` | Internal parser for pre-1.23.0 RST changelog format. | **KEEP-BUT-MODERNISE** |
| `AChangelog` | Abstract changelog version: loads YAML, caches data, yields `AChangelogEntry` items. | **KEEP** |
| `AChangelogs` | Abstract changelog collection: scans files, syncs from GitHub releases. | **KEEP** |
| `AInventories` | Abstract inventory manager: scans `objects.inv` files, syncs from GitHub archive. | **KEEP** |
| `AProject` | Abstract project: version read/write, release/dev/sync/publish/trigger lifecycle. | **KEEP** |
| `AProtobufSet` | Loads a compiled `FileDescriptorSet` binary and builds a `DescriptorPool`. | **KEEP** |
| `AProtobufValidator` | Validates YAML/JSON fragments against Envoy proto3 schemas. | **KEEP** |

**Notable issues:**

- `LegacyChangelog` is the RST-format changelog parser kept for pre-1.23 Envoy releases.
  All active Envoy versions are `>= 1.23`. The parser may no longer be exercised in
  practice — worth confirming whether any supported stable version is still `< 1.23`
  before removing it.
- `AProject._git_commit` constructs a `git commit` command via shell string concatenation
  with f-string escaping. This is fragile (escaping `"` and `` ` `` manually). The
  implementation should use `asyncio.create_subprocess_exec` with a list of args instead.
- `AChangelogs.datestamp` uses `datetime.utcnow()` which is deprecated in Python 3.12.
  Should be `datetime.now(tz=timezone.utc)`.
- `abstract/project/project.py` imports `asyncio.AbstractEventLoop` and `concurrent.futures.Executor`
  in `AProject.__init__` — these are passed to `directory_kwargs` but the `loop` parameter
  is deprecated in Python 3.10+ asyncio APIs.

**Module verdict:** `KEEP`. Complex, tested, and actively used in both toolshed and
`envoyproxy/envoy`. Several correctness issues to fix (see follow-up plan).

---

### `project.py`

~49 LOC. Concrete implementations of the project abstract layer.

| Symbol | Description | Verdict |
|---|---|---|
| `ChangelogEntry` | Concrete `IChangelogEntry` / `AChangelogEntry` implementation. | **KEEP** |
| `Changelog` | Concrete `IChangelog` / `AChangelog`; sets `entry_class = ChangelogEntry`. | **KEEP** |
| `Changelogs` | Concrete `IChangelogs` / `AChangelogs`; sets `changelog_class = Changelog`. | **KEEP** |
| `Inventories` | Concrete `IInventories` / `AInventories`. | **KEEP** |
| `Project` | Concrete `IProject` / `AProject`; uses `GitDirectory` and the concrete changelog/inventory classes. | **KEEP** |

**Module verdict:** `KEEP`. Thin wiring layer; correct.

---

### `protobuf.py` / `abstract/protobuf.py`

~19 LOC (concrete) + ~112 LOC (abstract).

| Symbol | Description | Verdict |
|---|---|---|
| `ProtobufSet` | Concrete `IProtobufSet` / `AProtobufSet`. | **KEEP** |
| `ProtobufValidator` | Concrete `IProtobufValidator` / `AProtobufValidator`; sets `protobuf_set_class = ProtobufSet`. | **KEEP** |

**In-repo consumers:** `envoy.docs.sphinx_runner` imports `ProtobufValidator`.

**Envoy consumers:** `docs/tools/protodoc/manifest_to_json.py` and `test/config_test/static_config_validation.py` both import `ProtobufValidator` directly. This is a core dependency for Envoy's config validation CI tooling.

**Module verdict:** `KEEP`. Actively used in `envoyproxy/envoy` CI and docs.

---

### `data_env.py` / `data_env_cmd.py`

~50 LOC. Serializes JSON/YAML data to a pickle file for consumption by Bazel genrules.

| Symbol | Description | Verdict |
|---|---|---|
| `DataEnvironment` | Class with `create(*args)` (serialize to pickle) and `load(*args)` (deserialize from pickle) classmethods; driven by `argparse`. | **KEEP** |
| `data_env_cmd` | Entry-point wrapper for `DataEnvironment.create`. | **KEEP** |

**Latent bug — critical:** Both `parser_create` and `parser_load` are decorated with
`@classmethod @property` (the "classproperty" pattern). This combination was **deprecated
in Python 3.11** (with a `DeprecationWarning`) and **removed in Python 3.13**. The inline
TODO comments acknowledge this but the fix has not been applied. If the package is ever run
on Python 3.13+ the `DataEnvironment.parser_create` access will raise `TypeError`. The
correct replacement is a plain `classmethod` factory or an `@staticmethod`.

**Module verdict:** `KEEP`. Actively used by `envoy_python.bzl` in `envoyproxy/envoy`
(`envoy_py_data` and `envoy_gencontent` rules). Fix the `@classmethod @property` bug.

---

### `jinja_env.py` / `jinja_env_cmd.py`

~74 LOC. Precompiles Jinja2 template environments for Bazel genrules.

| Symbol | Description | Verdict |
|---|---|---|
| `JinjaEnvironment` | Class with `create(*args)` (compile templates to a `.py` module) and `load(*args)` (load compiled env) classmethods. | **KEEP** |
| `jinja_env_cmd` | Entry-point wrapper for `JinjaEnvironment.create`. | **KEEP** |

**Same latent bug as `DataEnvironment`:** `parser_create` and `parser_load` use the
deprecated `@classmethod @property` combo. Same fix applies.

**Module verdict:** `KEEP`. Heavily used by `envoy_python.bzl` in `envoyproxy/envoy`
(`envoy_jinja_env` and `envoy_gencontent` rules). Fix the `@classmethod @property` bug.

---

### `fetch_runner.py` / `fetch_cmd.py`

~283 LOC. Async downloader: downloads files from a JSON-specified URL list, validates
checksums and GPG signatures, and optionally packs the results into a tarball.

| Symbol | Description | Verdict |
|---|---|---|
| `FetchRunner` | `aio.run.Runner` subclass; HTTP download with `aiohttp`, GPG validation with `python-gnupg`, concurrent fetching via `aio.core.tasks.concurrent`. | **KEEP** |
| `fetch_cmd` | Entry-point wrapper. | **KEEP** |

**Stdlib comparison:** `urllib.request` + `asyncio` could replace `aiohttp`, but
`aiohttp` provides streaming, session reuse, and chunked reads that make this non-trivial
to replace. GPG validation via `python-gnupg` wraps the `gpg` binary; no stdlib
replacement.

**Module verdict:** `KEEP`. Niche but important downloader for CI asset management. No
obvious stdlib replacement.

---

### `parallel_runner.py` / `parallel_cmd.py`

~65 LOC. Runs a shell command in parallel CPU-count-batched chunks.

| Symbol | Description | Verdict |
|---|---|---|
| `ParallelRunner` | `aio.run.Runner` subclass; splits items into `os.cpu_count()` batches and runs them concurrently via `asyncio.create_subprocess_shell`. | **KEEP-BUT-MODERNISE** |
| `parallel_cmd` | Entry-point wrapper. | **KEEP** |

**Stdlib comparison:** `asyncio.create_subprocess_shell` (used here) is stdlib.
`concurrent.futures.ProcessPoolExecutor` + `asyncio.to_thread` / `asyncio.TaskGroup`
(3.11+) would be cleaner alternatives. The manual batching logic (`math.ceil`,
`range(0, cpu_count)`) could be replaced by `itertools.batched` (Python 3.12+).

**In-repo consumers:** No Python code outside `envoy.base.utils` itself imports
`ParallelRunner` directly. Usage is through the `envoy.parallel` console script.

**Envoy consumers:** GitHub code search found no direct invocations of `envoy.parallel`
in the `envoyproxy/envoy` source. Likely called from shell scripts or Bazel rules not
visible in the search index.

**Module verdict:** `KEEP-BUT-MODERNISE`. The batching logic should use
`itertools.batched` (3.12+) and the subprocess handling should use
`asyncio.create_subprocess_exec` (list-of-args API) rather than shell string
concatenation.

---

### `project_runner.py` / `project_cmd.py` / `project_data_cmd.py`

~347 LOC. CLI runners for the project lifecycle (release, dev, sync, publish, trigger)
and for dumping project JSON data.

| Symbol | Description | Verdict |
|---|---|---|
| `BaseProjectRunner` | Shared base: project + session + GitHub token. | **KEEP** |
| `ProjectRunner` | Full project lifecycle runner (`sync`, `release`, `dev`, `publish`, `trigger` sub-commands). | **KEEP** |
| `ProjectDataRunner` | Dumps project JSON data (version, stable versions, releases). | **KEEP** |
| `project_cmd` | Entry-point for `ProjectRunner`. | **KEEP** |
| `project_data_cmd` | Entry-point for `ProjectDataRunner`. | **KEEP** |

**Consumers:** `envoyproxy/envoy` uses these runners via the `envoy.project` and
`envoy.project_data` console scripts (invoked by CI scripts for release management, though
the exact shell call sites are not in the repo's Python source).

**Module verdict:** `KEEP`. Central to Envoy's release automation.

---

## Consumer map

### envoyproxy/toolshed py/

| Consumer package | Symbols consumed | Call sites |
|---|---|---|
| `envoy.code.check` | `utils.interface.IProject` (type), `utils.typing.ChangelogSectionsDict`, `utils.typing.ChangeDict`, `utils.typing.ChangeList`, `utils.typing.ChangelogChangeSectionsDict`, `utils.typing.ChangelogDict`, `utils.exceptions.ChangelogParseError`, `utils.last_n_bytes_of`, `utils.typed` | 7 files |
| `envoy.dependency.check` | `utils.typed`, `utils.from_yaml`, `utils.dt_to_utc_isoformat`, `utils.is_sha` | 2 files |
| `envoy.distribution.verify` | `utils.from_yaml`, `utils.extract` | 2 files |
| `envoy.docs.sphinx_runner` | `utils.to_yaml`, `utils.typed`, `utils.from_yaml`, `utils.extract`, `utils.is_tarlike`, `utils.pack` | 1 file |
| `envoy.github.release` | `utils.is_tarlike`, `utils.extract` | 1 file |
| `envoy.gpg.sign` | `utils.tuple_pair`, `utils.repack` | 1 file |
| `py/tools/fuzzing` | `envoy.base.utils.yaml.EnvoyYaml` | 1 file |

**No in-repo consumers** for the following exported symbols:
`coverage_with_data_file`, `to_bytes`, `async_list`, `cd_and_return`, `to_yaml`
(outside of the sphinx_runner's single call), `TAR_EXTS`, `tar_mode`.

`to_yaml` has one call in `envoy.docs.sphinx_runner` but is trivially replaceable inline.

### envoyproxy/envoy

Reference: `tools/base/requirements.in` lists `envoy.base.utils>=0.5.10`.

| File | Symbols/scripts used |
|---|---|
| `tools/base/envoy_python.bzl` | `envoy.jinja_env` (console script via `py_console_script_binary`), `envoy.data_env` (console script via `py_console_script_binary`). Both used in `envoy_jinja_env()`, `envoy_py_data()`, and `envoy_gencontent()` Starlark macros. |
| `docs/tools/generate_version_histories.py` | `utils.minor_version_for`, `IProject`, `Project`, `Inventories` (direct class subclassing). |
| `docs/tools/protodoc/manifest_to_json.py` | `ProtobufValidator` (direct import and instantiation). |
| `test/config_test/static_config_validation.py` | `ProtobufValidator` (validates Envoy YAML config against Protobuf schemas). |
| `tools/api_proto_breaking_change_detector/buf_utils.py` | Indirect (via `envoy.base.utils` as a transitive dependency; not a direct importer visible in search). |
| `docs/tools/python/requirements.in` | `envoy.base.utils` listed as direct dependency. |

**Key observation:** `envoyproxy/envoy` subclasses `Project` directly in
`generate_version_histories.py`, overriding `inventories` to swap in a custom `CustomInventories`
class. This means the `Project` / `Inventories` / `AProject` / `AInventories` hierarchy is
a **public extension point**, not just an internal implementation.

---

## Console scripts / entry points

| Script name | Entry point | Used by |
|---|---|---|
| `envoy.data_env` | `envoy.base.utils:data_env_cmd` | `envoy_python.bzl` → `envoy_py_data` / `envoy_gencontent` rules in `envoyproxy/envoy`. Actively called in CI. |
| `envoy.jinja_env` | `envoy.base.utils:jinja_env_cmd` | `envoy_python.bzl` → `envoy_jinja_env` / `envoy_gencontent` rules in `envoyproxy/envoy`. Actively called in CI. |
| `envoy.fetch` | `envoy.base.utils:fetch_cmd` | Not found in `envoyproxy/envoy` source. Likely called from shell scripts in CI pipelines. |
| `envoy.parallel` | `envoy.base.utils:parallel_cmd` | Not found in `envoyproxy/envoy` Python source. Likely called from shell scripts. |
| `envoy.project` | `envoy.base.utils:project_cmd` | Central to Envoy release workflow. Called from CI scripts (not visible as Python imports). |
| `envoy.project_data` | `envoy.base.utils:project_data_cmd` | Companion to `envoy.project`. |

All six console scripts should be considered live and not removable without coordinated
changes to `envoyproxy/envoy` CI.

---

## Cross-cutting findings

### 1. `@classmethod @property` (classproperty) — active bug on Python 3.13

`data_env.py` and `jinja_env.py` both use:

```python
@classmethod  # type: ignore
@property
def parser_create(cls) -> argparse.ArgumentParser:
    ...
```

The `type: ignore` comment acknowledges that mypy flags this. Python deprecated the
`classmethod` + `property` stacking in **3.11** and **removed** it in **3.13**. On 3.13
the accessor raises `TypeError`. This is a latent P0 bug if the deployment Python is ever
upgraded to 3.13 (the build currently sets `python_requires >= 3.11`). The
fix is to convert to a plain `@staticmethod` (since the parser is stateless) or a factory
`@classmethod`.

### 2. `datetime.utcnow()` — deprecated in Python 3.12

`abstract/project/changelog.py` line 249:

```python
def datestamp(self) -> str:
    return datetime.utcnow().date().strftime(self.date_format)
```

`datetime.utcnow()` is deprecated since Python 3.12 (raises `DeprecationWarning`). Replace
with `datetime.now(tz=timezone.utc).date().strftime(self.date_format)`.

### 3. `pytz` as a dependency for one function

`pytz` is a full runtime dependency used in exactly one place:

```python
# utils.py
def dt_to_utc_isoformat(dt: datetime.datetime) -> str:
    date = dt.replace(tzinfo=pytz.UTC)
    return date.date().isoformat()
```

`datetime.timezone.utc` (stdlib, since Python 3.2) is a direct replacement.
Removing `pytz` saves a transitive dependency.

### 4. Type-hint modernisation debt

The codebase consistently imports container type hints from `typing` rather than
`collections.abc` or using built-in generic syntax:

| Current | Modern (3.9+) |
|---|---|
| `typing.Iterator` | `collections.abc.Iterator` |
| `typing.Generator` | `collections.abc.Generator` |
| `typing.AsyncGenerator` | `collections.abc.AsyncGenerator` |
| `typing.Callable` | `collections.abc.Callable` |
| `typing.Iterable` | `collections.abc.Iterable` |
| `typing.ItemsView` | `collections.abc.ItemsView` |
| `typing.KeysView` | `collections.abc.KeysView` |
| `typing.ValuesView` | `collections.abc.ValuesView` |
| `typing.Pattern` | `re.Pattern` |
| `typing.IO` | `typing.IO` (stdlib `IO` is still in `typing`; acceptable) |
| `Optional[X]` | `X \| None` |
| `Union[A, B]` | `A \| B` |

Affected files: `utils.py`, `interface.py`, `tar.py`, `abstract/project/changelog.py`,
`abstract/project/inventory.py`, `abstract/project/project.py`, `typing.py`.

### 5. `setup.cfg` packaging issues

- **Classifiers claim Python 3.8 / 3.9 support** but `python_requires = >=3.11`. The
  classifier list should be updated to `Programming Language :: Python :: 3.11`,
  `3.12`, etc., and the old ones removed.
- **`multidict` and `yarl`** are listed in `install_requires` but are not imported
  anywhere in the package source. They appear to be transitive dependencies of `aiohttp`
  that were erroneously promoted to direct requirements. Remove them.
- **`frozendict`** appears only in `project_runner.py` as a type for `NOTIFY_MSGS` and
  `COMMIT_MSGS`. Worth checking if the dependency is intentional or if a plain
  `dict` constant would suffice (the values are never mutated at runtime).
- **Python version classifiers** reference `3 :: Only` but not specific 3.11/3.12
  versions — follow the cleanup pattern from PR #4296 / #4303.

### 6. `tarfile.extract` CVE mitigation (path traversal)

`tar.py` calls `tar.extract(member, path=member_path)` without a `filter` argument.
Python 3.12 emits `DeprecationWarning` for this form; Python 3.14 will change the
default to the `"data"` filter. Pass `filter="data"` explicitly to silence the warning
and future-proof against path-traversal in malicious archives.

### 7. `AProject._git_commit` — string-based subprocess

`abstract/project/project.py` builds `git` command lines via string joining and then
passes them to `asyncio.subprocess.create_subprocess_shell`. This:
- Is fragile under paths/messages with embedded spaces or shell metacharacters (the
  manual `replace('"', …)` escaping is not robust).
- Should use `create_subprocess_exec` with a list of arguments, which avoids shell
  quoting entirely.

### 8. `asyncio.AbstractEventLoop` / `loop` parameter in `AProject.__init__`

`abstract/project/project.py` accepts `loop: asyncio.AbstractEventLoop | None = None`
and stores it for passing to directory operations. Since Python 3.10 the `loop` parameter
was removed from most asyncio higher-level APIs, and passing a custom loop is strongly
discouraged. This parameter is likely vestigial.

### 9. Test coverage gaps for `KEEP` / `KEEP-BUT-MODERNISE` symbols

The following symbols are flagged `KEEP` or `KEEP-BUT-MODERNISE` and have thin or
no dedicated test coverage:

- `tar.py` — `repack` is not directly tested (only indirectly via `extract`/`pack`).
- `fetch_runner.py` — `FetchRunner.validate_signature` path relies on calling GPG
  externally; the test file (`test_fetch_runner.py`) exists but GPG integration
  scenarios are not covered.
- `parallel_runner.py` — `ParallelRunner.batches` with edge cases (items count not
  evenly divisible by cpu_count) is not explicitly tested.

---

## Prioritized follow-up plan

### P0 — Fix before next release

1. **Fix `@classmethod @property` in `data_env.py` and `jinja_env.py`**
   Convert `parser_create` / `parser_load` to `@staticmethod` (they are stateless). This
   is a Python 3.13 breakage waiting to happen.
   *Single small PR; affects `DataEnvironment` and `JinjaEnvironment`.*

2. **Fix `tarfile.extract` filter deprecation in `tar.py`**
   Add `filter="data"` to the `tar.extract(member, path=…)` call in `_extract()`.
   *One-liner fix; addresses both the Python 3.12 warning and the path-traversal risk.*

3. **Fix `datetime.utcnow()` deprecation in `abstract/project/changelog.py`**
   Replace `datetime.utcnow()` with `datetime.now(tz=timezone.utc)`.
   *One-liner; silences Python 3.12 `DeprecationWarning`.*

### `KEEP-BUT-MODERNISE` items

4. **Replace `pytz` with stdlib `datetime.timezone.utc` in `utils.py`**
   `dt_to_utc_isoformat` is the only caller. Replace `pytz.UTC` → `datetime.timezone.utc`
   and drop `pytz` from `install_requires` and `types-pytz` from the types extra.
   *Small PR; removes a transitive dep.*

5. **Modernise type-hint imports across all modules**
   - Use `collections.abc.{Iterator,Generator,AsyncGenerator,Callable,Iterable,…}` instead
     of `typing.*` counterparts.
   - Use `re.Pattern` instead of `typing.Pattern`.
   - Replace `Optional[X]` / `Union[A, B]` with `X | None` / `A | B`.
   - Affects ~8 files; can be one PR.

6. **Replace `itertools.batched` in `parallel_runner.py`**
   The manual `range(0, cpu_count)` / slice batching is exactly what `itertools.batched`
   (Python 3.12+) does. Drop the `math.ceil` import.
   *3-line change.*

7. **Fix `ProjectDevResultDict = dict` in `typing.py`**
   Replace the bare `dict` alias with a proper `TypedDict` defining the known keys
   (`version`, `old_version`, `date`).
   *Small PR; improves type coverage for the dev workflow result.*

8. **Modernise `AChangelogs.datestamp` (see P0 item 3 above)**
   Already listed under P0 but the broader `datetime` audit of `abstract/project/` should
   be done in one pass.

9. **Refactor `AProject._git_commit` to use `create_subprocess_exec`**
   Replace shell-string concatenation with an arg-list call to
   `asyncio.create_subprocess_exec`. This removes the fragile escaping logic.
   *Medium PR; affects `abstract/project/project.py`.*

### `DEPRECATE` items

10. **Deprecate and remove `cd_and_return`**
    `contextlib.chdir` (3.11+) is a direct stdlib replacement. There are zero consumers
    outside `envoy.base.utils` itself, so no migration is needed in other packages.
    *One PR: emit `DeprecationWarning` in current version; remove in next minor.*

11. **Deprecate and remove `async_list`**
    Replace with inline `[x async for x in gen if not filter or filter(x)]`.
    Zero consumers outside `envoy.base.utils` itself.
    *Same release as `cd_and_return`.*

12. **Deprecate and remove `to_bytes`**
    Inline `data if isinstance(data, bytes) else data.encode()` everywhere.
    Zero consumers outside `envoy.base.utils` itself.
    *Same release.*

13. **Deprecate and remove `to_yaml`**
    Single external consumer (`envoy.docs.sphinx_runner`): replace with
    `path.write_text(yaml.dump(data))` inline.
    *Coordinate with `envoy.docs.sphinx_runner` PR.*

### `MOVE` items

14. **Move `coverage_with_data_file` out of `envoy.base.utils`**
    The file already has an inline comment saying this should move to `tools.testing.utils`
    or similar. Zero external consumers. Candidate destination: `py/envoy.code.check` or a
    new `envoy.testing.utils` package.
    *Low urgency; do when the right destination package is clear.*

### `setup.cfg` cleanup

15. **Clean up `setup.cfg`** (pattern from PR #4296 / #4303):
    - Remove Python 3.8 / 3.9 classifiers; add 3.11 / 3.12 classifiers.
    - Remove `multidict` and `yarl` from `install_requires` (transitive-only deps).
    - Re-evaluate `frozendict` (used only for two module-level constants).
    - Follow the `pyproject.toml` / `setup.cfg` modernisation pattern established in
      recent cleanup PRs.

### Long-term / investigate

16. **Assess whether `LegacyChangelog` is still needed**
    All current Envoy stable versions are `>= 1.23`. If the oldest supported stable
    version's changelog files are all in YAML format, the RST parser and its
    `RST_CHANGELOG_URL_TPL` can be removed. Verify by checking `envoyproxy/envoy`
    `stable_versions[-1]` against `YAML_CHANGELOGS_VERSION = "1.23"`.

17. **Document the `EnvoyYaml` global-mutation design decision**
    `envoy_yaml.yaml` mutates `yaml.SafeLoader` / `yaml.SafeDumper` globally. This should
    be a documented invariant (or refactored to a dedicated `Loader` subclass to avoid
    polluting all pyyaml users in the same process).
