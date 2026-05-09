# `aio.run.runner` publish-readiness review

Audit baseline: [`8664a051a61e3c9a4f55b3826b09efda6f4ec5e0`](https://github.com/envoyproxy/toolshed/tree/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0) (`main` at investigation start).

Assumptions for this review: the in-flight `aio.run.runner` packaging/typing cleanup is landed (normalized metadata, `python_requires>=3.12`, corrected classifiers, modern typing), and the `_on_runner_error` uvloop compatibility fix is landed.

## A. Public API inventory + verdict

| Symbol | What it does | Approx LOC | In-repo consumers across `py/` (unique files, grouped by package) | Verdict |
|---|---|---:|---|---|
| `Runner` | Base async CLI runner with argparse, logging setup, loop lifecycle, tempdir lifecycle, and error handling hooks. | ~222 ([`runner.py#L83-L304`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L83-L304)) | `py/envoy.base.utils`(6), `py/aio.api.bazel`(2), `py/aio.run.checker`(2), `py/envoy.ci.report`(2), `py/envoy.distribution.repo`(2), `py/envoy.docs.sphinx_runner`(2), `py/envoy.gpg.sign`(2), `py/envoy.github.abstract`(1), `py/aio.run.runner`(2) | **KEEP-BUT-MODERNISE** |
| `ACommand` | Abstract command object bound to a runner context, with command-local argparse flow. | ~26 ([`abstract.py#L17-L42`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/abstract.py#L17-L42)) | `py/envoy.github.abstract`(2), `py/envoy.distribution.release`(1) | **KEEP** |
| `ARunnerWithCommands` | `Runner` subclass with command registry/dispatch (`register_command`, `commands`, `command`, `run`). | ~21 ([`abstract.py#L48-L68`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/abstract.py#L48-L68)) | `py/envoy.github.abstract`(1) | **KEEP-BUT-MODERNISE** |
| `ICommand` | Interface contract for async command execution (`run`). | ~5 ([`abstract.py#L10-L14`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/abstract.py#L10-L14)) | No external consumers found in `py/` (test/internal references only in `py/aio.run.runner`) | **DEPRECATE** |
| `catches` | Async method decorator that catches configured exceptions, logs, and returns exit code `1`. | ~38 ([`decorators.py#L6-L43`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/decorators.py#L6-L43)) | `py/envoy.base.utils`(2), `py/envoy.ci.report`(1), `py/envoy.distribution.release`(1), `py/envoy.distribution.repo`(1), `py/envoy.docs.sphinx_runner`(1), `py/envoy.gpg.sign`(1), `py/aio.run.runner`(2) | **KEEP-BUT-MODERNISE** |
| `cleansup` | Async method decorator that always awaits `self.cleanup()` in `finally`. | ~19 ([`decorators.py#L46-L64`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/decorators.py#L46-L64)) | `py/aio.run.checker`(1), `py/envoy.base.utils`(2), `py/envoy.ci.report`(1), `py/envoy.distribution.release`(1), `py/envoy.distribution.repo`(1), `py/envoy.docs.sphinx_runner`(1), `py/envoy.gpg.sign`(1), `py/aio.run.runner`(3) | **KEEP-BUT-MODERNISE** |
| `runner` (submodule re-export in `__all__`) | Re-export of submodule object from package `__init__`. | ~8 package glue lines ([`__init__.py#L2-L17`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/__init__.py#L2-L17)) | Most consumers import `runner` via `from aio.run import runner`, not `from aio.run.runner import runner` (no direct matches found). | **DEPRECATE** |

**`runner` re-export verdict rationale:** it appears non-load-bearing for current in-repo consumers; `from aio.run import runner` is the dominant pattern (e.g. [`project_runner.py#L13`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/envoy.base.utils/envoy/base/utils/project_runner.py#L13), [`checker.py#L9`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.checker/aio/run/checker/checker.py#L9), [`abstract/runner.py#L16`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/envoy/ci/report/abstract/runner.py#L16)).

## B. Stdlib comparison (Python 3.12+)

- `Runner.__call__` + `start_reactor` + `install_reactor` still adds value beyond `asyncio.run` because it centralizes uvloop installation and a custom loop exception handler ([`runner.py#L89-L103`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L89-L103), [`runner.py#L245-L280`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L245-L280)).
- Compared to `asyncio.Runner`, current shape is mostly a manual lifecycle wrapper around `loop.run_until_complete`, but with extra policy hooks (`uvloop.install`, `set_exception_handler`, custom catastrophic cleanup path). This means migration is feasible, but not a must-fix.
- `on_async_error` + `set_exception_handler` is still bespoke behavior (default handler + hard `loop.stop`) and is not “free” from `asyncio.Runner` alone ([`runner.py#L250-L257`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L250-L257)).
- KeyboardInterrupt flow (`__call__` -> `_on_runner_error`) is explicit and understandable; a 3.12+ idiomatic alternative is a single outer `try/except KeyboardInterrupt` around an `asyncio.Runner` context, but this is quality work, not publish-blocking ([`runner.py#L97-L103`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L97-L103), [`runner.py#L297-L304`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L297-L304)).
- Logging lifecycle is functional but more bespoke than needed: direct mutation of private logging internals and root handlers is brittle vs `logging.config` style setup ([`runner.py#L176-L186`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L176-L186)).
- `add_arguments`/`args`/`extra_args`/`parser` usage is idiomatic argparse and straightforward ([`runner.py#L103-L112`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L103-L112), [`runner.py#L151-L156`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L151-L156), [`runner.py#L223-L236`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L223-L236)).
- `catches`/`cleansup` are async-only wrappers despite `cleansup` docstring claiming sync+async support; this should be reconciled (doc or implementation) ([`decorators.py#L46-L55`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/decorators.py#L46-L55)).
- `ACommand`/`ARunnerWithCommands` interface plumbing is still meaningful (used by `envoy.github.abstract` command runner stack) but thin; future refinements are mostly typing/API polish ([`envoy/github/abstract/command.py#L16-L42`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/envoy.github.abstract/envoy/github/abstract/command.py#L16-L42), [`envoy/github/abstract/runner.py#L14-L17`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/envoy.github.abstract/envoy/github/abstract/runner.py#L14-L17)).

## C. Bug / inconsistency check

- No `TypeError`-shape forwarding bugs found in this package: `*args/**kwargs` forwarding in decorators is correct ([`decorators.py#L29-L35`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/decorators.py#L29-L35), [`decorators.py#L53-L58`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/decorators.py#L53-L58)).
- No remaining `asyncio.get_event_loop()` usage in `py/aio.run.runner`.
- No `asyncio.ensure_future` usage in `py/aio.run.runner`.
- No `gather(create_task(...))` / `create_task` modernization debt inside this package.
- Deprecated stdlib call still present: `logging.warn(...)` in uvloop import fallback should be `logging.warning(...)` ([`runner.py#L18-L23`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L18-L23)).
- Logging setup has brittle assumptions (private dict mutation and direct handler indexing) that are not currently failing tests but are fragile under alternate root logger states ([`runner.py#L176-L186`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L176-L186)).
- Tempdir lifecycle warning path is in place and tested; it reliably warns when `tempdir` is touched and `run` appears undecorated ([`runner.py#L199-L209`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L199-L209), [`runner.py#L283-L289`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L283-L289), [`test_runner.py#L415-L439`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/tests/test_runner.py#L415-L439)).

## D. Security / runtime hygiene

- No `subprocess.run(..., shell=True)` patterns found in `py/aio.run.runner`.
- Tempdir usage is via `TemporaryDirectory` and explicit cleanup (`cleanup` + `_cleanup_tempdir`) ([`runner.py#L238-L240`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L238-L240), [`runner.py#L291-L295`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L291-L295)).
- Bootstrapping order mostly protects logging before reactor start (`setup_logging` before `start_reactor`), reducing early exception blind spots in normal flow ([`runner.py#L266-L280`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/runner.py#L266-L280)).

## E. Test coverage gaps relevant to publishing

- Public symbols are broadly directly covered (`Runner`, `ACommand`, `ARunnerWithCommands`, `ICommand`, `catches`, `cleansup`) in package tests ([`test_runner.py`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/tests/test_runner.py), [`test_abstract.py`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/tests/test_abstract.py), [`test_decorators.py`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/tests/test_decorators.py)).
- Gap: no direct test asserting the package export contract in `__all__` (especially `runner` re-export behavior) ([`__init__.py#L10-L17`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/aio/run/runner/__init__.py#L10-L17)).
- No tests patch `asyncio.get_event_loop` or `asyncio.ensure_future` in this package test suite.
- `_on_runner_error` tests are tightly coupled to current implementation details (`new_event_loop`, `set_event_loop`, `run_until_complete`, `close`) and will likely need reshaping when the uvloop compatibility PR lands fully ([`test_runner.py#L699-L758`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/tests/test_runner.py#L699-L758)).

## F. Publish-readiness checklist

- ✅ Packaging metadata correct (post-cleanup PR assumption).
- ✅ Typing modernised (post-cleanup PR assumption).
- ⚠️ No latent stdlib bugs — deprecated `logging.warn` remains; logging setup is still brittle on private internals/handler assumptions (see **C**).
- ✅ uvloop>=0.21 compatibility (assuming in-flight `_on_runner_error` fix lands as stated).
- ⚠️ Public API surface is intentional — `runner` submodule export appears non-load-bearing; `ICommand` has no external in-repo consumers (see **A**).
- ⚠️ Test coverage on public surface — no explicit test for `__all__` export contract, and `_on_runner_error` tests are implementation-coupled (see **E**).
- ✅ Dependency pins sane — current dependency floor is `aio.core>=0.11.0` in package metadata, which aligns with the post-`aio.core` cleanup baseline ([`setup.cfg#L29-L35`](https://github.com/envoyproxy/toolshed/blob/8664a051a61e3c9a4f55b3826b09efda6f4ec5e0/py/aio.run.runner/setup.cfg#L29-L35)).
- ✅ No security-sensitive patterns surviving.

## G. Recommended action plan

### Must-fix before publish

- Replace deprecated `logging.warn` and harden logging setup assumptions (avoid unconditional private map mutation / handler index assumptions). Files: `py/aio.run.runner/aio/run/runner/runner.py`. Impact: **small**. Behaviour-changing: **low**.
- Add focused tests for package export contract (`__all__`) and for final post-fix `_on_runner_error` behavior (semantic, not implementation-detail assertions). Files: `py/aio.run.runner/tests/test_runner.py` (and/or new small test module). Impact: **small**. Behaviour-changing: **no**.

### Should-fix before publish

- Deprecate `runner` re-export from `aio.run.runner.__all__` (announce and keep temporary compatibility), and evaluate whether `ICommand` should stay public. Files: `py/aio.run.runner/aio/run/runner/__init__.py`, package docs/changelog. Impact: **tiny**. Behaviour-changing: **potentially** (if removal follows deprecation).
- Reconcile `cleansup` contract/docs (either document async-only explicitly or implement true sync+async support). Files: `py/aio.run.runner/aio/run/runner/decorators.py`, tests. Impact: **small**. Behaviour-changing: **possibly**.

### Can-defer

- Refactor lifecycle to `asyncio.Runner` context-management while preserving uvloop installation and current error/cleanup semantics. Files: `py/aio.run.runner/aio/run/runner/runner.py`, tests. Impact: **medium**. Behaviour-changing: **yes**.
- Typing polish for command abstractions (stronger context typing/generics, optional `@override` once adopted repo-wide). Files: `py/aio.run.runner/aio/run/runner/abstract.py` and downstream consumers. Impact: **small**. Behaviour-changing: **no**.

**Bottom line:** ship after a short pre-publish pass that fixes the deprecated/brittle logging edges and adds a couple of focused tests; no major architectural blocker remains for PyPI publication in the assumed post-cleanup state.
