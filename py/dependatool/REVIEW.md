# `dependatool` — code review

_Generated 2026-05-10. Follow-up to the initial packaging cleanup pass._

## Summary

`dependatool` is small and readable, but most of its complexity comes from framework scaffolding and copy-pasted per-ecosystem checkers rather than domain logic. The core behavior (compare `dependabot.yml` directories vs files found in-repo) is simple, yet schema handling is shallow and brittle, and tests are heavily implementation-coupled while missing key behavior coverage (`docker`, `npm`, CLI, malformed configs). Recommendation: **invest only in a narrow hardening pass needed for safe publish/consumption, then accelerate retirement** rather than deeper feature expansion.

## Findings

### 1. Architectural / API-surface smells

#### 1.1 Four near-identical checker implementations increase maintenance cost
- **Where**: `py/dependatool/dependatool/docker/abstract.py:L17-L83`, `py/dependatool/dependatool/gomod/abstract.py:L17-L83`, `py/dependatool/dependatool/npm/abstract.py:L17-L83`, `py/dependatool/dependatool/pip/abstract.py:L16-L82` ([docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L17-L83), [gomod](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/gomod/abstract.py#L17-L83), [npm](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/npm/abstract.py#L17-L83), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/pip/abstract.py#L16-L82))
- **What**: The implementations differ mostly by ecosystem name and filename pattern.
- **Why it matters**: Any bug fix or behavior change must be repeated 4 times, which increases drift risk.
- **Suggested fix**: Introduce one generic ecosystem checker with class constants (ecosystem id, filename matcher, success/error labels), keep thin subclasses only if needed.
- **Effort**: M
- **Risk**: medium

#### 1.2 Public API surface is inconsistent (`npm` is wired but not exported)
- **Where**: `py/dependatool/dependatool/__init__.py:L2-L23` and `py/dependatool/dependatool/checker.py:L24-L30` ([__init__](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/__init__.py#L2-L23), [checker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/checker.py#L24-L30))
- **What**: `npm` checks are active in runtime wiring, but `ADependatoolNPMCheck`/`DependatoolNPMCheck` are not re-exported from package top-level while other ecosystems are.
- **Why it matters**: External consumers get a surprising/incomplete API and may treat `npm` as unsupported.
- **Suggested fix**: Either export `npm` consistently or make all ecosystem classes intentionally private/internal.
- **Effort**: S
- **Risk**: low

#### 1.3 Thin pass-through classes/files do not earn their own abstraction
- **Where**: `py/dependatool/dependatool/docker/check.py:L8-L10`, `py/dependatool/dependatool/gomod/check.py:L8-L10`, `py/dependatool/dependatool/npm/check.py:L8-L10`, `py/dependatool/dependatool/pip/check.py:L8-L10` ([docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/check.py#L8-L10), [gomod](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/gomod/check.py#L8-L10), [npm](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/npm/check.py#L8-L10), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/pip/check.py#L8-L10))
- **What**: Four files each define a single `pass` subclass.
- **Why it matters**: More files/imports without behavior, which increases navigation overhead.
- **Suggested fix**: Collapse to one implementation module unless subclass hooks are actually needed.
- **Effort**: S
- **Risk**: low

### 2. Dependabot config parsing correctness

#### 2.1 Schema validation is effectively absent
- **Where**: `py/dependatool/dependatool/abstract/checker.py:L43-L51` and ecosystem config comprehensions (`docker/abstract.py:L27-L30`, `gomod/abstract.py:L27-L30`, `npm/abstract.py:L27-L30`, `pip/abstract.py:L26-L29`) ([checker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/abstract/checker.py#L43-L51), [docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L27-L30), [gomod](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/gomod/abstract.py#L27-L30), [npm](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/npm/abstract.py#L27-L30), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/pip/abstract.py#L26-L29))
- **What**: Only top-level `dict` type is checked; required keys/types inside `updates` are assumed.
- **Why it matters**: Malformed `dependabot.yml` can crash with raw `KeyError`/`TypeError` instead of actionable diagnostics.
- **Suggested fix**: Validate schema shape up front (`version`, `updates` list, per-update required keys and types), and raise domain-specific errors with field paths.
- **Effort**: M
- **Risk**: medium

#### 2.2 Unknown/extra fields and schema drift are silently ignored
- **Where**: same config extraction paths above, especially direct filtering by `package-ecosystem` and `directory` only ([docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L27-L30))
- **What**: The parser disregards all fields except ecosystem and directory.
- **Why it matters**: Changes in upstream schema or user mistakes can pass unnoticed, producing false confidence.
- **Suggested fix**: Emit warnings for unknown/missing expected fields, and optionally strict-mode fail on unsupported schema constructs.
- **Effort**: M
- **Risk**: medium

### 3. YAML / data hygiene

#### 3.1 Positive: YAML load path uses `safe_load`
- **Where**: `py/dependatool/dependatool/abstract/checker.py:L45-L46` via `aio.core.utils.from_yaml` in `py/aio.core/aio/core/utils/data.py:L52-L57` ([checker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/abstract/checker.py#L45-L46), [safe_load](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/aio.core/aio/core/utils/data.py#L52-L57))
- **What**: Load path is safe with respect to arbitrary YAML object construction.
- **Why it matters**: Avoids a common unsafe YAML pitfall.
- **Suggested fix**: Keep this behavior; add explicit tests for malformed YAML and non-dict documents.
- **Effort**: S
- **Risk**: low

#### 3.2 Hard-coded config path and ignored directories are magic constants
- **Where**: `py/dependatool/dependatool/abstract/checker.py:L16-L23` ([link](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/abstract/checker.py#L16-L23))
- **What**: `DEPENDABOT_CONFIG` and ignore regexes are static and not externally configurable.
- **Why it matters**: Harder to reuse in non-Envoy layouts; changes require code edits.
- **Suggested fix**: Support CLI flags and/or config/env overrides for config path and ignore patterns.
- **Effort**: S
- **Risk**: low

### 4. Async correctness

#### 4.1 Async is used for mostly synchronous set operations
- **Where**: ecosystem `check()` methods (`docker/abstract.py:L44-L65`, `gomod/abstract.py:L44-L65`, `npm/abstract.py:L44-L65`, `pip/abstract.py:L43-L64`) ([docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L44-L65), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/pip/abstract.py#L43-L64))
- **What**: The only awaited work is reading file lists; the rest is synchronous set math and message formatting.
- **Why it matters**: Adds framework complexity in a package whose core logic is small.
- **Suggested fix**: Consider a synchronous implementation or isolate async to one repo-scan stage with pure sync validation thereafter.
- **Effort**: M
- **Risk**: medium

#### 4.2 Unused `files` parameter in all check methods
- **Where**: `check(self, files=None)` in `abstract/check.py:L13-L14` and all ecosystem implementations (`docker/abstract.py:L44`, `gomod/abstract.py:L44`, `npm/abstract.py:L44`, `pip/abstract.py:L43`) ([abstract](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/abstract/check.py#L13-L14), [docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L44))
- **What**: API advertises input override but implementations ignore it.
- **Why it matters**: Misleads callers and blocks efficient targeted checks.
- **Suggested fix**: Either remove `files` from the contract or wire it through and test it.
- **Effort**: S
- **Risk**: low

### 5. Error handling & exit-code discipline

#### 5.1 Parsing errors are not normalized into actionable config errors
- **Where**: direct key access in ecosystem config extraction (`docker/abstract.py:L27-L30`, `gomod/abstract.py:L27-L30`, `npm/abstract.py:L27-L30`, `pip/abstract.py:L26-L29`) ([docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L27-L30), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/pip/abstract.py#L26-L29))
- **What**: Malformed entries can raise raw exceptions rather than contextual messages (`updates[i].directory` missing, wrong type, etc.).
- **Why it matters**: CI users see stack traces without clear remediation.
- **Suggested fix**: Catch and wrap parse/shape failures with field-level context and stable exit semantics.
- **Effort**: M
- **Risk**: medium

#### 5.2 Exception naming is ecosystem-specific but used globally
- **Where**: `py/dependatool/dependatool/exceptions.py:L3-L4` and usage in `abstract/checker.py:L13,L48-L50` ([exception](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/exceptions.py#L3-L4), [usage](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/abstract/checker.py#L13-L50))
- **What**: `PipConfigurationError` is raised for global dependabot config parse failures.
- **Why it matters**: Error taxonomy is misleading now that non-pip ecosystems are first-class checks.
- **Suggested fix**: Rename to neutral `DependatoolConfigurationError` (or equivalent) and map consistently.
- **Effort**: S
- **Risk**: low

### 6. CLI / entry-point

#### 6.1 CLI is a thin passthrough with no package-specific argument contract documented or tested
- **Where**: `py/dependatool/dependatool/cmd.py:L7-L16` and test target contents in `py/dependatool/tests/BUILD:L2` + test files list (`test_abstract_checker.py`, `test_checker.py`, `test_gomod_abstract_check.py`, `test_pip_abstract_checker.py`) ([cmd](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/cmd.py#L7-L16), [tests BUILD](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/tests/BUILD#L2))
- **What**: CLI behavior is implicit through inherited checker behavior; no dedicated CLI tests in this package.
- **Why it matters**: Regressions in argument/exit behavior can slip through while unit tests remain green.
- **Suggested fix**: Add a small CLI behavior test matrix (`--help`, bad path/config, success/failure exit code).
- **Effort**: S
- **Risk**: medium

### 7. Logging / observability

#### 7.1 Error/success messages omit high-value context
- **Where**: message emission in `docker/abstract.py:L74-L82`, `gomod/abstract.py:L74-L82`, `npm/abstract.py:L74-L82`, `pip/abstract.py:L73-L81` ([docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L74-L82), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/pip/abstract.py#L73-L81))
- **What**: Messages include directory names but not config path, update index, or source line details.
- **Why it matters**: Slower incident triage in CI when large configs are involved.
- **Suggested fix**: Include config path and failing update metadata in emitted messages.
- **Effort**: S
- **Risk**: low

#### 7.2 Ignored directories are silently dropped with no audit trail
- **Where**: dir filtering in `docker/abstract.py:L66-L72`, `gomod/abstract.py:L66-L72`, `npm/abstract.py:L66-L72`, `pip/abstract.py:L65-L71` ([docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L66-L72), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/pip/abstract.py#L65-L71))
- **What**: Matches under ignored paths disappear without any warning/debug output.
- **Why it matters**: Can hide unexpected omissions and make policy debugging harder.
- **Suggested fix**: Add optional debug-level reporting for ignored matches.
- **Effort**: S
- **Risk**: low

### 8. Type-annotation correctness

#### 8.1 Public APIs use broad/unparameterized types
- **Where**: `check_tools` return types omitted in `abstract/checker.py:L37-L40` and `checker.py:L24-L30`; `config(self) -> set` and `errors(self, missing: Iterable, ...)` in ecosystem classes (e.g. `pip/abstract.py:L24-L25,L73-L74`) ([abstract checker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/abstract/checker.py#L37-L40), [checker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/checker.py#L24-L30), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/pip/abstract.py#L24-L74))
- **What**: Types are either missing or too generic to constrain contracts.
- **Why it matters**: Weak static guarantees around parser output and checker wiring.
- **Suggested fix**: Add precise signatures (`dict[str, ADependatoolCheck]`, `set[str]`, `Iterable[str]`) and shared TypedDict/Protocol for config entries.
- **Effort**: S
- **Risk**: low

#### 8.2 Unexplained `# type:ignore` hides a typing mismatch
- **Where**: `py/dependatool/dependatool/abstract/checker.py:L71-L74` ([link](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/abstract/checker.py#L71-L74))
- **What**: Property declaration suppresses type checking without nearby explanation.
- **Why it matters**: Makes future typing regressions harder to evaluate.
- **Suggested fix**: Remove the ignore by aligning abstract property typing, or document the exact mypy limitation in code.
- **Effort**: S
- **Risk**: low

### 9. Testing smells

#### 9.1 Coverage gap: no `docker`, `npm`, or CLI-focused tests
- **Where**: test files are limited to `test_abstract_checker.py`, `test_checker.py`, `test_gomod_abstract_check.py`, `test_pip_abstract_checker.py` under `py/dependatool/tests/`; no corresponding docker/npm/cmd test modules (test target in `py/dependatool/tests/BUILD:L2`) ([BUILD](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/tests/BUILD#L2))
- **What**: Two ecosystems and entry-point behavior are effectively untested in-package.
- **Why it matters**: Drift and regressions are likely in the least-covered paths.
- **Suggested fix**: Add behavior tests for docker/npm parity and CLI exit behavior.
- **Effort**: M
- **Risk**: medium

#### 9.2 Tests are heavily implementation-coupled (mock internals + call-arg assertions)
- **Where**: e.g. `test_abstract_checker.py:L52-L57,L77-L104`, `test_gomod_abstract_check.py:L70-L78,L126-L145`, `test_pip_abstract_checker.py:L71-L78,L109-L128` ([abstract checker tests](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/tests/test_abstract_checker.py#L52-L104), [gomod tests](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/tests/test_gomod_abstract_check.py#L70-L145), [pip tests](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/tests/test_pip_abstract_checker.py#L71-L128))
- **What**: Many assertions validate exact call choreography instead of external behavior.
- **Why it matters**: Refactors that preserve behavior can still break tests, reducing test value.
- **Suggested fix**: Shift toward black-box tests over sample repo trees and real yaml snippets.
- **Effort**: M
- **Risk**: medium

#### 9.3 Missing malformed-config edge-case tests
- **Where**: current config tests only cover happy-path key presence (`test_gomod_abstract_check.py:L21-L33`, `test_pip_abstract_checker.py:L23-L34`, `test_abstract_checker.py:L29-L58`) ([gomod](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/tests/test_gomod_abstract_check.py#L21-L33), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/tests/test_pip_abstract_checker.py#L23-L34), [checker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/tests/test_abstract_checker.py#L29-L58))
- **What**: No tests for missing `updates`, wrong types, or malformed update entries.
- **Why it matters**: Current brittle parsing behavior is unguarded.
- **Suggested fix**: Add failure-case tests first, then tighten parser behavior.
- **Effort**: S
- **Risk**: low

### 10. Dead / duplicated / commented-out code

#### 10.1 Internal TODOs suggest unfinished API and stale backlog in a small package
- **Where**: `py/dependatool/dependatool/abstract/checker.py:L25-L27,L85` ([link](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/abstract/checker.py#L25-L85))
- **What**: TODOs include unimplemented checks and an internal method intended to be public.
- **Why it matters**: Signals partially completed design and unclear maintenance intent.
- **Suggested fix**: Convert TODOs into issues or remove/comment with retirement plan.
- **Effort**: S
- **Risk**: low

#### 10.2 Minor nits
- **Where**: ecosystem `check()` signatures include unused `files` arg (`docker/abstract.py:L44`, `gomod/abstract.py:L44`, `npm/abstract.py:L44`, `pip/abstract.py:L43`) ([docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L44), [pip](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/pip/abstract.py#L43))
- **What**: Parameter currently has no effect.
- **Why it matters**: Low-level API noise and reader confusion.
- **Suggested fix**: remove or implement.
- **Effort**: S
- **Risk**: low

### 11. Documentation

#### 11.1 Public docs still describe this as pip-only
- **Where**: `py/dependatool/README.rst:L5` and `py/dependatool/setup.cfg:L10` ([README](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/README.rst#L5), [setup.cfg](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/setup.cfg#L10))
- **What**: Description claims “Pip dependabot checker” despite docker/gomod/npm checks being present.
- **Why it matters**: Misleads users about scope and support.
- **Suggested fix**: Update README/package description to reflect actual ecosystems and limits.
- **Effort**: S
- **Risk**: low

#### 11.2 Copy-paste docstrings are stale/inaccurate
- **Where**: e.g. `docker/abstract.py:L34-L46` and `gomod/abstract.py:L34-L46`; the current docstrings literally say `dockerfile.txt`/`gomodfile.txt` while runtime matching uses `Dockerfile*` and `go.mod` file names ([docker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/docker/abstract.py#L34-L46), [gomod](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/gomod/abstract.py#L34-L46))
- **What**: Comments/docstrings no longer match behavior.
- **Why it matters**: Increases reviewer/operator confusion.
- **Suggested fix**: Refresh docstrings as part of the next cleanup PR.
- **Effort**: S
- **Risk**: low

### 12. Retirement signals

#### 12.1 High framework + maintenance overhead for narrow functionality
- **Where**: framework-heavy base class inheritance (`abstract/checker.py:L30-L33`), per-ecosystem duplication (`docker/gomod/npm/pip abstract modules`), runtime deps in `setup.cfg:L29-L33` ([checker](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/abstract/checker.py#L30-L33), [setup deps](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/setup.cfg#L29-L33))
- **What**: Simple directory-consistency checks are wrapped in substantial scaffolding and duplicated code.
- **Why it matters**: Ongoing schema/tooling drift costs likely outweigh value for this package.
- **Suggested fix**: Do a minimal hardening/publish pass, then retire into a simpler shared check (or fold into an existing dependency-checking package).
- **Effort**: L (for migration), S/M (for immediate hardening)
- **Risk**: medium

#### 12.2 Support boundary is unclear, increasing long-term stewardship risk
- **Where**: inconsistent API/docs (`__init__.py:L2-L23`, `README.rst:L5`, `setup.cfg:L10`) and missing test coverage for parts of surface (`tests/BUILD:L2`) ([__init__](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/dependatool/__init__.py#L2-L23), [README](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/README.rst#L5), [tests](https://github.com/envoyproxy/toolshed/blob/b18f135755dedb4a50e6309c88bfdd3b6f616931/py/dependatool/tests/BUILD#L2))
- **What**: It is unclear what is public, what is tested, and what is intentionally supported.
- **Why it matters**: Ambiguous support boundaries are a strong retirement signal for small utility packages.
- **Suggested fix**: If retained, define support contract explicitly; otherwise deprecate and set sunset date.
- **Effort**: S
- **Risk**: low

## Recommended follow-up PRs

1. **PR-1: Harden dependabot schema parsing and error messages** (Findings: 2.1, 5.1, 9.3, 7.1)
   - Add explicit schema validation for `version`, `updates`, and required update keys/types.
   - Convert malformed-input failures into contextual, stable user-facing errors.
   - **Effort**: M
   - **Risk**: medium

2. **PR-2: Add missing behavior tests for docker/npm/CLI and malformed input** (Findings: 6.1, 9.1, 9.3)
   - Add black-box tests for docker/npm parity and command exit semantics.
   - Add malformed/missing-field yaml test matrix.
   - **Effort**: M
   - **Risk**: medium

3. **PR-3: Consolidate ecosystem checker duplication** (Findings: 1.1, 1.3, 10.2)
   - Replace copy-paste implementations with a generic checker core + minimal descriptors.
   - **Effort**: M
   - **Risk**: medium

4. **PR-4: Clarify/normalize public API + exception naming** (Findings: 1.2, 5.2, 8.1, 8.2)
   - Decide and document public exports (`npm` included or all internals hidden).
   - Rename exception taxonomy and tighten type signatures.
   - **Effort**: S
   - **Risk**: low

5. **PR-5: Documentation and observability cleanup** (Findings: 3.2, 7.2, 11.1, 11.2)
   - Update README/metadata/docstrings for true ecosystem support and limits.
   - Add optional debug logs for ignored directories and parse decisions.
   - **Effort**: S
   - **Risk**: low

6. **PR-6: Retirement/deprecation decision PR** (Findings: 12.1, 12.2)
   - If retiring, document replacement path and timeline; if retaining, document support boundary.
   - **Effort**: S
   - **Risk**: low
