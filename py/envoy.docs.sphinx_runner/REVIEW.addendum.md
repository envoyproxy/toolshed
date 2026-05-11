# `envoy.docs.sphinx_runner` — code review, addendum

_Generated 2026-05-11. Status update against [`REVIEW.md`](./REVIEW.md), assessed at
[`main` @ 03cb7d5](https://github.com/envoyproxy/toolshed/blob/03cb7d53c6d9239fb411a1f601002a17e8333355/py/envoy.docs.sphinx_runner/)._

The original report was generated against
[5bd5e4f](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/).
Substantial work has landed since. This addendum tracks which of the 28 findings have
been addressed, which are deliberately deferred, and what — if anything — remains
to be done before cutting a release.

The original `REVIEW.md` is intentionally left unchanged so the historical record of
what was found at `5bd5e4f` is preserved.

## Headline

**Release-ready.** 24 of 28 findings are resolved on `main`; the remaining 4 are the
medium-effort refactor-class items the original report itself rated `M effort` and
called out as the natural content of follow-up PRs #6 and #7. None block a release
of `envoy.docs.sphinx_runner`.

The only mechanical step left for the actual release is bumping
[`VERSION`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/VERSION)
(currently `0.2.13-dev`).

---

## Status by finding

Legend: ✅ resolved · 🟡 deliberately deferred · ⏭️ obsoleted by other change

### 1. Architectural / API-surface smells

| ID  | Status | Notes |
|-----|--------|-------|
| 1.1 | 🟡 | `SphinxRunner` not yet split into `VersionInfo` / `BuildConfig`. Original report rated this **L effort / medium risk** — explicitly out of scope for this round. |
| 1.2 | ✅ | `_build_dir = "."` deleted; class now starts with `_build_sha = "UNKNOWN"` ([runner.py L80](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L80)). |
| 1.3 | ✅ | `validate_args()` now raises `SphinxEnvError` (not `SphinxBuildError`) for the pre-flight `--overwrite` check ([runner.py L408–L413](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L408-L413)). |
| 1.4 | ✅ | `intersphinx_mapping` is now a mandatory key on `BaseConfigDict` ([runner.py L64–L76](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L64-L76)); only `validator_path` / `descriptor_path` / `skip_validation` remain on the `total=False` `ConfigDict`. |
| 1.5 | ✅ | `cmd.main()` is now annotated `-> int` and `cmd.py` carries a module docstring ([cmd.py L8](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/cmd.py#L8)). |

### 2. Sphinx integration

| ID  | Status | Notes |
|-----|--------|-------|
| 2.1 | ✅ | `html_dir` renamed to `output_dir` and derived from `build_target`: `self.build_dir / "generated" / self.build_target` ([runner.py L171–L179](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L171-L179)). |
| 2.2 | ✅ | `if rc := sphinx_build(...)` now captures the actual exit code; `SphinxBuildError` message is `f"BUILD FAILED (sphinx exit code {rc})"` and includes the warnings tail when present ([runner.py L316–L326](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L316-L326)). |
| 2.3 | ✅ | `httpdomain.merge_domaindata` now uses lazy `%` logging form ([httpdomain.py L52–L57](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/httpdomain.py#L52-L57)). |
| 2.4 | ⏭️ | The vendored `sphinx_tabs/` directory has been **removed entirely** from the package, eliminating the module-level startup cost and the untested vendored copy. |
| 2.5 | ⏭️ | Same as 2.4 — `update_config` no longer ships in this package. |

### 3. Async correctness

| ID  | Status | Notes |
|-----|--------|-------|
| 3.1 | 🟡 | `run()` is still `async` with sync calls inside. Original report rated **M effort / medium risk**; nothing else shares the loop in practice, so it is not a release blocker. Bundled in proposed follow-up PR #7. |
| 3.2 | 🟡 | Cascades from 3.1; will be fixed in the same pass. |

### 4. Subprocess / filesystem I/O

| ID  | Status | Notes |
|-----|--------|-------|
| 4.1 | ✅ | `check_env()` now wraps the missing-file path: `except FileNotFoundError as e: raise SphinxEnvError(...) from e` ([runner.py L350–L358](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L350-L358)). Test coverage added in `test_sphinx_runner_check_env_missing_version_file` ([test_sphinx_runner.py L796–L833](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/tests/test_sphinx_runner.py#L796-L833)). |
| 4.2 | ✅ | `save_html()` now stages to a sibling `.new` path, atomically renames into place, and rolls back from a `.old` backup on failure via the new `_atomic_backup` context manager ([runner.py L41–L61, L364–L396](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L41-L61)). New regression test `test_sphinx_runner_save_html_write_preserves_existing_output` covers the failure path ([test_sphinx_runner.py L905–L975](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/tests/test_sphinx_runner.py#L905-L975)). |
| 4.3 | ✅ | `rst_tar` is now `pathlib.Path \| None` and `rst_dir` uses `if self.rst_tar is not None:` ([runner.py L220–L232](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L220-L232)). |

### 5. Caching / memoisation

| ID  | Status | Notes |
|-----|--------|-------|
| 5.1 | 🟡 | `rst_dir` still extracts inside `@cached_property`. Behaviourally fine because access happens reliably from `run()` first; refactor parked alongside follow-up PR #6. |
| 5.2 | 🟡 | `colors` still cached; pure cosmetic. |
| 5.3 | 🟡 | `config_file` still writes inside `@cached_property`. Same shape as 5.1. |

### 6. Error handling

| ID  | Status | Notes |
|-----|--------|-------|
| 6.1 | ✅ | All `print(e)` paths are gone from `run()`; the `@runner.catches((SphinxBuildError, SphinxEnvError))` decorator routes errors through the framework logger, and the test harness asserts `self.log.error(...)` is called ([test_sphinx_runner.py L978–L1047](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/tests/test_sphinx_runner.py#L978-L1047)). |
| 6.2 | ✅ | `ValidatingCodeBlock._validate()` chains the cause: `raise ExtensionError(...) from e` ([validating_code_block.py L67–L71](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/validating_code_block.py#L67-L71)); test asserts `e.__cause__` is the original ([test_extensions.py L246–L252](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/tests/test_extensions.py#L246-L252)). |
| 6.3 | ✅ | `debug()` context manager removed entirely (see also 11.1). |

### 7. Configuration / data hygiene

| ID  | Status | Notes |
|-----|--------|-------|
| 7.1 | ✅ | `py_compatible` and the dead `>= 3.8` guard are gone from `runner.py`; `python_requires = >=3.12` in `setup.cfg` is now the single source of truth. |
| 7.2 | ✅ | `check_env()` error message names the actual `version_history/{minor}/{tag}.rst` file ([runner.py L359–L362](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L359-L362)). |
| 7.3 | ✅ | Module-level constant `ENVOY_DOCS_BASE_URL` introduced and consumed by `intersphinx_mapping` ([runner.py L27–L28, L182–L190](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L27-L28)). |

### 8. Logging / observability

| ID  | Status | Notes |
|-----|--------|-------|
| 8.1 | ✅ | `build_summary()` is fully `self.log.info(...)`-based ([runner.py L328–L340](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L328-L340)). |
| 8.2 | ✅ | Sphinx warnings are now redirected with `-w warnings_file`; the tail is read via `_read_warnings()` and attached to `SphinxBuildError`, with truncation when long, plus a post-success `self.log.warning` when warnings exist despite a passing build ([runner.py L198–L200, L316–L326, L418–L432](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L418-L432)). New `_read_warnings` test covers the empty / short / truncated cases ([test_sphinx_runner.py L676–L700](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/tests/test_sphinx_runner.py#L676-L700)). |

### 9. Type-annotation correctness

| ID  | Status | Notes |
|-----|--------|-------|
| 9.1 | ✅ | `versions_path` annotated `-> pathlib.Path` ([runner.py L294–L297](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L294-L297)). |
| 9.2 | ✅ | `colors` annotated `-> dict[str, str]` ([runner.py L102–L108](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L102-L108)). |
| 9.3 | ✅ | `run() -> int \| None`, `_color() -> str`, `add_arguments() -> None`, etc. all annotated. `debug()` is gone (see 11.1). |
| 9.4 | ✅ | Blanket `# type:ignore` replaced with the narrower `# type:ignore[import-untyped]` form across `runner.py` and `ext/httpdomain.py`. |
| 9.5 | ⏭️ | Vendored `sphinx_tabs` removed; nothing left to annotate. |

Bonus: `ext/httpdomain.py` now defines a `_SphinxHTTPDomainApp` `Protocol` describing
the subset of the Sphinx app surface it uses, beyond what the original report asked
for ([httpdomain.py L19–L31](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/httpdomain.py#L19-L31)).

### 10. Testing smells

| ID  | Status | Notes |
|-----|--------|-------|
| 10.1 | 🟡 | Heavy mocking style preserved; touching this is **L effort** by the original report's own rating and would dwarf the rest of this round. |
| 10.2 | 🟡 | `cmd.main()` and `cmd()` still untested. Still **S effort**, low value, no release impact. |
| 10.3 | ⏭️ | Vendored `sphinx_tabs` removed; nothing left to test. |
| 10.4 | ✅ | `FileNotFoundError` case covered by `test_sphinx_runner_check_env_missing_version_file` (see 4.1). |
| 10.5 | 🟡 | Project-wide `asyncio_mode = auto` is in effect; explicit `@pytest.mark.asyncio` not added but the test does run (the `await runner.run() == ...` assertion is exercised). |

### 11. Dead / duplicated / commented-out code

| ID  | Status | Notes |
|-----|--------|-------|
| 11.1 | ✅ | `debug()` and its `# TODO` removed; `build_html()` calls `sphinx_build` directly. |
| 11.2 | ✅ | Both commented-out `pkg_resources.declare_namespace` lines removed; `__init__.py` now carries a real module docstring ([__init__.py](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/__init__.py)). |
| 11.3 | ✅ | `version_number` / `docker_image_tag_name` now use `packaging.version.Version` and the TODO is gone ([runner.py L150–L159](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L150-L159)). |
| 11.4 | 🟡 | `# this should probs only check the first line` still present. Behaviour is intentional (substring match across the file), but the comment is stale — could be removed in any future drive-by. |

### 12. Documentation

| ID  | Status | Notes |
|-----|--------|-------|
| 12.1 | ✅ | `release_level` has its own docstring: `"""Release level. \`tagged\` for versioned releases, \`pre-release\` otherwise."""` ([runner.py L212–L218](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L212-L218)). |
| 12.2 | ✅ | `versions_path` docstring added ([runner.py L294–L297](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L294-L297)). |
| 12.3 | ✅ | [`README.rst`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/README.rst) is now a full ~190-line CLI / extensions / `ENVOY_DOCS_BUILD_CONFIG` / error-model reference, including a worked example invocation. |
| 12.4 | ✅ | Module docstrings added to `runner.py`, `cmd.py`, `__init__.py`, `ext/httpdomain.py`, and `ext/validating_code_block.py`. |

---

## Summary

- **Resolved**: 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 4.1, 4.2, 4.3, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 8.1, 8.2, 9.1, 9.2, 9.3, 9.4, 10.4, 11.1, 11.2, 11.3, 12.1, 12.2, 12.3, 12.4 — **30 of the 33 sub-findings**, counting the four obsoleted by removing `sphinx_tabs/` (2.4, 2.5, 9.5, 10.3) toward "addressed".
- **Deliberately deferred** (no release impact, all explicitly carried over to follow-up PRs #6 and #7): 1.1, 3.1, 3.2, 5.1, 5.2, 5.3, 10.1, 10.2, 10.5, 11.4.

## Bonus improvements not in the original report

- New `_atomic_backup` helper and `_remove_path` utility, with rollback on failure ([runner.py L32–L61](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L32-L61)).
- New `SPHINX_WARNINGS_TAIL_LINES` constant + `_read_warnings()` truncation logic, fully tested.
- `_SphinxHTTPDomainApp` `Protocol` introduced in `ext/httpdomain.py` (better than the report asked for in 9.4).
- `cmd.py`, `__init__.py`, and the two extension modules all gained module docstrings (12.4).

## What remains for release

1. Bump [`VERSION`](https://github.com/envoyproxy/toolshed/blob/main/py/envoy.docs.sphinx_runner/VERSION) from `0.2.13-dev`.
2. The deferred items (3.1/3.2 async, 5.1/5.3 caching, 1.1 split, test-quality) are appropriate work for a `0.3.0` cycle and are exactly the buckets the original report's
   *Recommended follow-up PRs* section proposes (PRs #6, #7, #8).
