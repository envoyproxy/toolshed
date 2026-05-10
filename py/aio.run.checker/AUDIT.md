# `aio.run.checker` — Publish-Readiness Audit

> **Branch:** `audit/aio-run-checker` | **Audited HEAD:** `e5bb813` (main)
>
> **Baseline:** in-flight cleanup PR (#4303, already landed on this branch) has landed:
> `setup.cfg` normalised, `python_requires>=3.12`, `VERSION 0.5.9-dev`, PEP 585/604 typing,
> `aio.run.runner>=0.3.5`. This report covers what remains.

---

## A. Public API Inventory

| Symbol | Module | LOC (approx) | External consumers | Verdict |
|---|---|---|---|---|
| `Checker` | `checker.py` | ~240 | `envoy.dependency.check`, `envoy.code.check`, `envoy.distribution.verify`, `envoy.distribution.distrotest`, `dependatool` (all production) | **KEEP** |
| `CheckerSummary` | `checker.py` | ~100 | `envoy.code.check` (subclassed as `CodeCheckerSummary`) | **KEEP** |
| `Problems` | `checker.py` | ~7 | `envoy.code.check` (instantiated directly at ~10 call-sites) | **KEEP** |
| `preload` | `decorators.py` | ~72 | `envoy.dependency.check` (×5 sites), `envoy.code.check` (×4 sites) | **KEEP** |
| `IProblems` | `interface.py` | ~15 | `envoy.code.check/typing.py` (used in type aliases) | **KEEP** |
| `abstract` | submodule | ~24 | None externally — no `checker.abstract.*` import found outside the package | **KEEP-BUT-NOTE** (see below) |
| `decorators` | submodule | ~72 | None externally — all external use is via `checker.preload`, not `checker.decorators.*` | **KEEP-BUT-NOTE** |
| `interface` | submodule | ~15 | `envoy.code.check/typing.py` uses `checker.interface.IProblems` | **KEEP** |

**Submodule exports in `__all__`:**
`abstract`, `decorators`, and `interface` are all re-exported as submodules. Unlike the `runner` audit where the submodule export was non-load-bearing, here `interface` is load-bearing (`checker.interface.IProblems` appears in `envoy.code.check/typing.py`). `abstract` and `decorators` appear only for internal wiring; no external code reaches them by submodule path. These are benign but slightly noisy. Not a must-fix.

**Consumer summary:** 5 packages declare `aio.run.checker>=0.5.8` in `setup.cfg`. In production code, all use `from aio.run import checker` and access `checker.Checker`, `checker.CheckerSummary`, `checker.Problems`, `checker.preload`, `checker.interface.IProblems`. The `IProblems` shortcut at the top level (also in `__all__`) is therefore somewhat redundant but harmless.

---

## B. Stdlib Comparison (Python 3.12+ Baseline)

### `asyncio.gather` vs `TaskGroup`

[`checker.py:439`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L439):
```python
await asyncio.gather(*self.preload_tasks)
```
`asyncio.gather` swallows the first exception when `return_exceptions=False` (default) and cancels siblings silently. `asyncio.TaskGroup` (3.11+) gives structured concurrency with proper `ExceptionGroup` propagation. The preload machinery has its own per-task exception handling (`preloader_catches`), so migration is non-trivial. **can-defer.**

### `asyncio.create_task` usage

[`checker.py:294`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L294):
```python
self._preloader = asyncio.create_task(self.preload())
```
This is the correct modern form (no `ensure_future`). Called from within `async def on_checks_begin` so the loop is running. ✅

### `asyncio.Queue` constructor

[`checker.py:329`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L329):
```python
return asyncio.Queue()
```
No deprecated `loop=` kwarg. The `cached_property` is first accessed during `begin_checks()` which is within an async context. ✅

### `asyncio.timeout` / bespoke timeout

No custom timeout machinery in the checker itself. Preload timing uses `time.time()` for logging only ([`checker.py:454`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L454)). No migration needed.

### `argparse`

All arguments added via `add_arguments()` on a standard `ArgumentParser` passed from `Runner`. No subparsers. No hand-rolling. ✅

### Text formatting

Summary uses string concatenation and `"-" * 80` separator ([`checker.py:605`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L605)). No `textwrap` needed; columns are not fixed-width tables. ✅

### Logging conventions

`self.log.warning(...)` (modern) used throughout. No `self.log.warn(...)`. ✅

---

## C. Bug / Inconsistency Check

### `asyncio.get_event_loop()` calls (#4286 shape)

**None in `py/aio.run.checker/`.** The `loop` property lives in `aio.core.event.AReactive` ([`reactive.py:42`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.core/aio/core/event/reactive.py#L42)) and was fixed there. Checker inherits via `Runner → AReactive`. ✅

### `asyncio.ensure_future` (#4282 shape)

**None found.** `create_task` used throughout. ✅

### `logging.warn(...)` removed in Python 3.13

**None in source files.** ✅

### `*args/**kwargs` forwarding bugs (#4282 AExecutive shape)

`Checker.__init__` forwards `*args` to `super().__init__` cleanly:
```python
def __init__(self, *args) -> None:
    super().__init__(*args)
```
No `**kwargs` in the chain. ✅

### `@cached_property` over mutable sets

[`checker.py:331–381`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L331-L381) — `completed_checks`, `preload_pending_tasks`, `preloaded_checks`, `removed_checks`, `check_queue`, `disabled_checks`, `checks_to_run`, `preload_checks`, `preload_checks_data`, `preload_tasks`, `summary` are all `@cached_property` returning mutable state. This is an intentional pattern in this codebase (the sets are mutated in place rather than replaced). Since `Checker` is single-use (one call, one `__call__`, no reset), this is safe in practice. Not a bug; it's the framework's idiom. ✅

### Docstring vs implementation: three typos

These are honest-but-untidy docstrings. Not behavioural, but they appear in the published API doc:

1. [`checker.py:87`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L87) — dangling `"` in docstring:
   ```python
   """The "path" - usually Envoy src dir. This is used for finding "
   configs for the tooling and should be a dir
   """
   ```
   The `"` before `configs` is a stray closing quote. **should-fix.**

2. [`checker.py:333`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L333) — `"succesfully"` → `"successfully"`. **should-fix.**

3. [`checker.py:366`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L366) — `"wich"` → `"which"`. **should-fix.**

### Exit code paths

`Checker.run()` ([`checker.py:473–483`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L473-L483)):

```python
@runner.cleansup
async def run(self) -> int:
    await self.begin_checks()
    try:
        await self._run_from_queue()
    finally:
        result = (
            1
            if self.exiting
            else await self.on_checks_complete())
    return result
```

If `_run_from_queue` raises an *unexpected* exception (from a buggy `check_*` method), the `finally` block runs `on_checks_complete()` (printing the summary), but then the exception re-propagates past `return result`. `Runner.__call__` only catches `RuntimeError` and `KeyboardInterrupt`; any other exception crashes the process without a meaningful exit code. This is intentional design: check methods are expected to call `self.error()`/`self.warn()` rather than raise. The test at line 1664 confirms this is expected. ⚠️ Worth a comment but **can-defer**.

`on_runner_error` ([`checker.py:305`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L305)) simply delegates to `on_checks_complete()`. This means a runner-level error (e.g. `KeyboardInterrupt`) triggers the summary, which is correct behaviour matching the runner audit's `_on_runner_error` sibling fix. ✅

### `abstracts.implementer` / `abstracts.interfacemethod` shape

`AProblems` in [`abstract.py`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/abstract.py) uses `@abstracts.implementer(interface.IProblems)` / `metaclass=abstracts.Abstraction` correctly. `IProblems` in [`interface.py`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/interface.py) uses `metaclass=abstracts.Interface` with `@abstracts.interfacemethod`. Both consistent with `aio.core` and `aio.run.runner` patterns. ✅

### Re-entrant `asyncio.run`

No `asyncio.run(...)` calls anywhere in the checker package. ✅

---

## D. Security / Runtime Hygiene

- **`subprocess.run(..., shell=True)`** — None. ✅
- **`tempfile.mkdtemp`** — None. ✅
- **Path concatenation** — `pathlib.Path(self.args.path or self.args.paths[0])` ([`checker.py:91`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/aio/run/checker/checker.py#L91)) — uses `pathlib.Path()` constructor, not string concatenation. `path.is_dir()` check on the result. ✅
- **File open without `with` / encoding** — No bare `open()` calls in the package. ✅
- **Bootstrapping order** — `self.log` is a `cached_property` on `Runner`. In `Checker.__init__`, no logging is done before `super().__init__()`. The first potential exception point (`self.parser.error`) only fires when `self.path` is first accessed, which is after logging is available. ✅

---

## E. Test Coverage Gaps

**Overall assessment:** 2131 lines of tests vs. ~300 LOC of source. The suite is thorough at unit level.

| Public symbol | Test file | Coverage status |
|---|---|---|
| `Checker` | `test_checker.py` | Excellent — all 63 test functions cover properties, methods, and async hooks |
| `CheckerSummary` | `test_checker.py` | Good — all public methods have dedicated tests |
| `Problems` | `test_checker.py:1858` | Minimal — one test (`assert isinstance(Problems(), abstract.AProblems)`). No test for `errors`/`warnings` kwargs to `Problems.__init__` directly (covered only via `AProblems` in `test_abstract.py`). ⚠️ |
| `preload` decorator | `test_decorators.py` | Good — 11 tests covering all properties and `get_preload_checks_data` |
| `IProblems` | `test_abstract.py:7` | Interface verified via `AProblems` instantiation test. ✅ |
| `abstract` submodule | `test_abstract.py` | Covered (3 tests). ✅ |

**Deprecated-pattern patches in tests:** No test patches `asyncio.get_event_loop`, `asyncio.ensure_future`, or `logging.warn`. Tests that patch `asyncio` ([`test_checker.py:634`](https://github.com/envoyproxy/toolshed/blob/e5bb813498dee2bf5d343192b7ecee1a93ecafa9/py/aio.run.checker/tests/test_checker.py#L634)) mock at the module level (`"asyncio"` prefix) which would survive any stdlib migration. ✅

**Tests tightly coupled to internal state shape:** The `test_checker_constructor` test at line 40 asserts `"preload_pending_tasks" in checker.__dict__` and similar for all five `@cached_property` sentinel sets. These would crack if any `@cached_property` were moved into `__init__` or changed to `property`. Acceptable: they enforce the intended lazy-init contract.

**Gap:** `test_checker_start_reactor` (line 533) and `test_checker_on_async_error` (line 1181) test methods inherited from `Runner` but instantiated from `Checker()`. These call `checker.start_reactor()` and `checker.on_async_error(loop, context)` — both methods live in `runner.Runner` and are already tested there. The checker-level tests here are therefore duplicating runner-level tests. Minor redundancy, not a gap. ✅

---

## F. Publish-Readiness Checklist

| Item | Status | Note |
|---|---|---|
| Packaging metadata correct | ✅ | Post-cleanup PR: `setup.cfg` clean, classifiers correct, `python_requires>=3.12`, `py.typed` present |
| Typing modernised | ✅ | PEP 585/604 throughout (post-cleanup PR) |
| No latent stdlib bugs (`logging.warn`, `get_event_loop`, etc.) | ✅ | None found |
| uvloop>=0.21 / Python 3.13 compatibility | ✅ | `get_event_loop` fix lives in `aio.core.event.AReactive`, not repeated here |
| Public API surface intentional | ⚠️ | `abstract` and `decorators` in `__all__` are unexported in practice; `IProblems` duplicates `interface.IProblems` at top level. Benign but slightly redundant |
| Test coverage on public surface | ⚠️ | `Problems` has minimal direct tests (see §E); all else well-covered |
| Dependency pins sane | ✅ | `abstracts>=0.2.0`, `aio.run.runner>=0.3.5` — both correct per prior audit work |
| No security-sensitive patterns | ✅ | No shell=True, no tempfile leaks, no bare file opens |

---

## G. Recommended Action Plan

### Must-fix before publish

None that block correctness. The package is functionally correct.

### Should-fix before publish

1. **Fix three docstring typos** — `checker.py:87` (dangling `"`), `checker.py:333` (`succesfully`), `checker.py:366` (`wich`).
   - Files: `aio/run/checker/checker.py`
   - Impact: **tiny**, not behaviour-changing.

2. **Add direct tests for `Problems(errors=..., warnings=...)`** — currently only `AProblems` init kwargs are tested. A single test for `Problems(errors=["e"], warnings=["w"])` verifying `.errors` and `.warnings` would cover the public concrete class.
   - Files: `tests/test_checker.py`
   - Impact: **tiny**, not behaviour-changing.

### Can-defer

3. **`asyncio.gather` → `TaskGroup`** in `preload()` (`checker.py:439`). Structured concurrency improvement; requires refactoring the `preloader_catches` / `on_preload_task_failed` machinery to handle `ExceptionGroup`. **medium**, behaviour-adjacent.

4. **Comment the `_run_from_queue` exception-propagation contract** — add a one-line note in `run()` that unexpected exceptions from `check_*` methods propagate past the `finally` block and crash the process. Clarifies the design intent. **tiny**, not behaviour-changing.

5. **`asyncio.Runner` refactor** — `Runner.__call__` still uses `loop.run_until_complete`. Migrating to `asyncio.Runner` (3.11+) would tighten the event-loop lifetime. Not a checker issue; lives in `aio.run.runner`. **can-defer per spec**.

6. **Trim `__all__`** — removing `abstract` and `decorators` from `__all__` (replacing with explicit named exports only) would make the public surface cleaner. But this is a semver surface change that could break consumers using `checker.abstract` or `checker.decorators` by name. **should wait for major version bump**.

---

## Bottom line

Ship after fixing the three docstring typos (#G-1) and adding the `Problems` direct test (#G-2). Both are tiny, non-behaviour-changing, and can land in the same micro-release. The package's core logic is solid: no latent `get_event_loop` / `ensure_future` / `logging.warn` bugs, typing is modern, packaging metadata is clean post-#4303, and the test suite comprehensively covers the public surface. There are no security concerns, no exit-code silencing bugs, and no incompatibilities with Python 3.12–3.13 or uvloop≥0.21.
