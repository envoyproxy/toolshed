# `py/aio.api.github` publish-readiness review

Baseline commit audited: `07e69a338fff168fb56ea6e7b2d4e794f52e68cc` (`main` at review start).

Context: packaging/typing cleanup has already landed (`0.2.11.dev0`, `python_requires>=3.12`, modernized type syntax) ([setup.cfg](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/setup.cfg#L1-L58), [PR #4304](https://github.com/envoyproxy/toolshed/pull/4304), [PR #4306](https://github.com/envoyproxy/toolshed/pull/4306)).

## A. Public API inventory + verdict

Package layout under `aio/api/github/`: top-level API (`api.py`, `interface.py`, `exceptions.py`, `utils.py`) plus `abstract/*` internals and an `abstract/stream/*` subtree that exists on disk but is not in package BUILD sources ([layout](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github), [BUILD sources](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/BUILD#L11-L32), [stream](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/stream/__init__.py#L1-L9)).

Top-level public surface is `__all__` in [`aio/api/github/__init__.py`](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/__init__.py#L54-L100).

Consumer counts below are in-repo runtime references grouped by package (excluding `py/aio.api.github/*` itself).

| Symbol | What | ~LOC | In-repo consumers | Verdict |
|---|---|---:|---|---|
| `abstract` | abstract submodule re-export | 33 | none found | KEEP-BUT-MODERNISE (internal-facing; document status) |
| `exceptions` | exception submodule re-export | 20 | `envoy.base.utils`, `envoy.dependency.check` | KEEP |
| `interface` | interface submodule re-export | 575 | `envoy.ci.report` | KEEP (load-bearing) |
| `utils` | datetime helper submodule re-export | 13 | none found | KEEP |
| `AGithubAPI` | base API wrapper | 113 | none direct | KEEP |
| `AGithubActions` / `AGithubWorkflows` | abstract Actions/workflows | 19 / 36 | none direct | KEEP |
| `AGithubRepo` | repo wrapper root | 174 | none direct | KEEP |
| `AGithubIterator` | async iterator + `total_count` | 84 | none direct | KEEP-BUT-MODERNISE |
| `AGithubIssue` / `AGithubIssues` | issue model/search/create wrappers | 39 / 70 | none direct | KEEP |
| `AGithubIssuesTracker` / `AGithubTrackedIssue` / `AGithubTrackedIssues` | tracked-issue framework | 13 / 62 / 149 | `envoy.dependency.check` | KEEP (load-bearing) |
| `AGithubCommit` / `AGithubTag` / `AGithubLabel` | entity wrappers | 11 / 9 / 5 | none direct | KEEP |
| `AGithubRelease` / `AGithubReleaseAssets` | release + asset upload wrappers | 63 / 63 | none direct | KEEP-BUT-MODERNISE |
| `GithubAPI` | concrete API wrapper | 48 | `envoy.base.utils`, `envoy.ci.report`, `envoy.dependency.check` | KEEP (load-bearing) |
| `GithubActions`, `GithubWorkflows`, `GithubRepo`, `GithubIterator`, `GithubIssues`, `GithubIssue`, `GithubRelease`, `GithubReleaseAssets`, `GithubCommit`, `GithubTag`, `GithubLabel` | thin concrete wrappers over abstract classes | 2–5 each | none direct | KEEP-BUT-MODERNISE (very thin but expected default wiring) |
| `IGithubAPI` | API interface | 90 | `envoy.base.utils`, `envoy.ci.report`, `envoy.dependency.check` | KEEP (load-bearing) |
| `IGithubRepo` | repo interface | 102 | `envoy.base.utils`, `envoy.ci.report`, `envoy.dependency.check` | KEEP (load-bearing) |
| `IGithubIssuesTracker` / `IGithubTrackedIssues` / `IGithubTrackedIssue` | tracker interfaces | 16 / 141 / 67 | `envoy.dependency.check` | KEEP (load-bearing) |
| `IGithubRelease` / `IGithubTag` / `IGithubCommit` | release/tag/commit interfaces | 21 / 2 / 2 | `envoy.dependency.check` | KEEP |
| `IGithubActions`, `IGithubWorkflows`, `IGithubIssues`, `IGithubIssue`, `IGithubIterator`, `IGithubLabel`, `IGithubReleaseAssets` | additional interfaces | 2–29 each | none direct (runtime) | KEEP-BUT-MODERNISE (broad surface, mostly type-contract utility) |

Load-bearing evidence examples: [`AProject.github -> GithubAPI`](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/envoy.base.utils/envoy/base/utils/abstract/project/project.py#L91-L96), [`DependencyChecker.github -> GithubAPI`](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/envoy.dependency.check/envoy/dependency/check/abstract/checker.py#L117-L123), [`AReportRunner.github -> GithubAPI`](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/envoy.ci.report/envoy/ci/report/abstract/runner.py#L39-L44), [`github.interface.IGithubRepo` type use](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/envoy.ci.report/envoy/ci/report/interface.py#L11-L15).

## B. Stdlib + library comparison (Python 3.12+ baseline)

1. **`asyncio.gather` vs `TaskGroup`**: package uses `aio.core.tasks.concurrent` for fan-out (asset uploads), not `TaskGroup` ([release assets push](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/release.py#L109-L118)). **can-defer**.
2. **`asyncio.timeout`**: no timeout context usage in package; HTTP calls rely on upstream session defaults via gidgethub methods ([AGithubAPI](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/api.py#L112-L126)). **should-fix** (document/allow per-call timeout propagation).
3. **`aiohttp.ClientSession` lifetime**: package accepts an injected session and does not create/close one internally ([constructor + session property](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/api.py#L26-L33), [session accessor](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/api.py#L98-L101)). This is clean, but ownership is implicit. **can-defer** (doc clarity).
4. **`yarl.URL`**: URL query interpolation uses string formatting (asset names, workflow IDs) without URL-encoding ([`artefact_url`](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/release.py#L105-L108), [`dispatch`](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/actions/actions.py#L66-L68)). **should-fix**.
5. **`packaging.version.Version`**: release/tag parsing uses `packaging.version.parse` with `InvalidVersion` handling ([release version property](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/release.py#L78-L83)). **keep**.
6. **`gidgethub` over-wrapping**: several methods are nearly pass-through wrappers (`getitem/post/patch/getiter`) ([AGithubAPI wrappers](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/api.py#L112-L126), [AGithubRepo wrappers](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/repo.py#L99-L107)). **can-defer** (API ergonomics vs duplication).
7. **Caching**: package already uses `cached_property`/`async_property` broadly ([examples](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/issues/tracker.py#L134-L205)). **keep**.
8. **JSON parsing**: no `json.loads(await response.text())` anti-pattern in this package. **keep**.

## C. Bug / inconsistency check

- `asyncio.get_event_loop()` / `ensure_future` / `logging.warn` / `asyncio.run`: none found in package sources.
- **Pagination total-count bug (must-fix):** `count_url` always appends `&per_page=1`, which is invalid when original query has no `?` ([iterator](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/iterator.py#L50-L55)); current test locks in that behavior ([test](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/tests/test_abstract_iterator.py#L97-L100)).
- **Pagination/header parsing fragility (must-fix):** `count_from_headers` assumes a specific `Link` header ordering/index and can miscount; fallback returns `0` when no `Link` and no `total_count`, even if items exist ([iterator](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/iterator.py#L73-L94)).
- **Exception forwarding/cause chain (should-fix):** `IssueCreateError` wraps `gidgethub.GitHubException` without `raise ... from e` and embeds raw exception text (`Recieved` typo included) ([issues.create](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/issues/issues.py#L93-L97)).
- `abstracts.implementer` / `interfacemethod`: shape is consistent across abstract/interface classes ([interface](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/interface.py#L17-L575), [abstract](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/__init__.py#L1-L33)).
- **Rate-limit handling:** iterator decrements `remaining` manually before request and rewrites `api.rate_limit` from response parse ([iterator](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/iterator.py#L57-L90)); behavior is non-standard and fragile. **should-fix**.
- Session close-on-error and re-entrant `asyncio.run`: not applicable within this package (session ownership is injected).
- Timeout defaults: no per-call timeout in wrapper surface. **should-fix** (at least document expected caller behavior).

## D. Security / runtime hygiene

- **Token redaction:** no direct token logging in this package; token is passed through to gidgethub header creation ([count request headers](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/iterator.py#L42-L47)) and workflow dispatch ([dispatch](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/actions/actions.py#L61-L69)).
- **Leak risk in exception text:** `IssueCreateError` includes raw upstream exception string; depending on upstream formatting this can expose sensitive request context. **should-fix** ([issues.create](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/issues/issues.py#L93-L97)).
- TLS verification bypass (`ssl=False`/`verify=False`): none found.
- Subprocess/shell usage: none found.
- Tempfile handling: none present.
- File I/O hygiene: binary open/read patterns are context-managed where used ([stream reader/writer](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/stream/_reader.py#L48-L54), [writer](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/stream/_writer.py#L31-L36)); note stream subtree is currently not part of BUILD sources.
- **URL construction injection/encoding hygiene:** string interpolation for query/path fields should be encoded (`asset name`, `workflow`) ([release assets](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/release.py#L105-L108), [actions dispatch](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/aio/api/github/abstract/actions/actions.py#L66-L68)). **should-fix**.
- `raise ... from err` chaining: missing in known wrapper path above. **should-fix**.

## E. Test coverage gaps relevant to publishing

- Public symbols with **no direct tests** (zero mentions in `py/aio.api.github/tests/*`): `IGithubActions`, `IGithubCommit`, `IGithubIssue`, `IGithubLabel`, `IGithubRepo`, `IGithubTag`, `IGithubWorkflows` (interface coverage is partial via parametrized subset only: [test_interface.py](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/tests/test_interface.py#L7-L15)).
- No tests patching `get_event_loop` / `ensure_future` / `logging.warn` (good).
- **Pagination bug is currently test-enshrined** (`QUERY&per_page=1` expectation) ([test](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/tests/test_abstract_iterator.py#L97-L100)).
- Network mocking: tests are fully mocked; no live GitHub/API traffic and no direct `aiohttp.ClientSession()` use in package tests.
- **Missing auth-header paranoia test:** no test verifies that failures do not log/token-leak sensitive auth data. **should-fix**.

## F. Publish-readiness checklist

- ✅ Packaging metadata correct (post-cleanup baseline) — [setup.cfg](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/setup.cfg#L1-L58).
- ✅ Typing modernised (post-cleanup baseline).
- ⚠️ No latent stdlib/runtime bugs — `total_count` URL/header logic is brittle/wrong for some queries (§C).
- ✅ uvloop>=0.21 / Python 3.13 compatibility blockers (`get_event_loop`, `logging.warn`) not present.
- ⚠️ Public API surface intentional but broad/thin in places (`IGithub*` + pass-through wrappers) (§A, §B).
- ⚠️ Test coverage on public surface is partial (several public interfaces untested directly; missing token-redaction test) (§E).
- ✅ Dependency pins sane (`aio.core>=0.11.0`, `aiohttp>=3.8.1`, `gidgethub`, `multidict>=6.0.2`, `packaging>=23.0`, `yarl>=1.7.2`) — [setup.cfg](https://github.com/envoyproxy/toolshed/blob/07e69a338fff168fb56ea6e7b2d4e794f52e68cc/py/aio.api.github/setup.cfg#L29-L36).
- ⚠️ No security-sensitive patterns surviving — mostly clean, but exception text and URL quoting need tightening (§D).
- ⚠️ Network-facing hygiene — timeout semantics and error-cause chaining should be clearer/safer (§B, §C, §D).

## G. Recommended action plan

### Must-fix before publish

1. Fix `AGithubIterator.total_count` URL building and `Link` parsing robustness (no blind `&per_page=1`, resilient parsing/fallback semantics).  
   Files: `abstract/iterator.py`, `tests/test_abstract_iterator.py`  
   Impact: **small**  
   Behavior-changing: **yes** (correct count behavior).

2. Correct pagination count behavior for non-search endpoints when `Link`/`total_count` is absent, or explicitly document unsupported semantics and fail loudly.  
   Files: `abstract/iterator.py`, tests  
   Impact: **small**  
   Behavior-changing: **yes**.

### Should-fix before publish

1. Preserve exception cause chains and sanitize wrapped GitHub error text in issue-creation failures.  
   Files: `abstract/issues/issues.py`, tests  
   Impact: **tiny**  
   Behavior-changing: **no** (except clearer error shape).

2. URL-encode path/query interpolations for workflow names and asset names (prefer `yarl.URL` composition).  
   Files: `abstract/actions/actions.py`, `abstract/release.py`  
   Impact: **small**  
   Behavior-changing: **yes** (safer URL construction).

3. Add paranoia tests for auth/token non-leak behavior on exceptions/logging paths.  
   Files: `tests/test_abstract_issues.py` (and related)  
   Impact: **tiny**  
   Behavior-changing: **no**.

4. Add direct tests for currently untested public interfaces in `__all__` (or explicitly narrow/clarify support policy).  
   Files: `tests/test_interface.py`  
   Impact: **tiny**  
   Behavior-changing: **no**.

### Can-defer

1. `TaskGroup` migration from `aio.core.tasks.concurrent` where useful.  
   Files: `abstract/release.py`  
   Impact: **small**  
   Behavior-changing: **no**.

2. Clarify/document timeout ownership contract (wrapper receives externally managed `ClientSession`).  
   Files: `README.rst`, interface docs  
   Impact: **tiny**  
   Behavior-changing: **no**.

3. Re-evaluate thin pass-through wrappers and oversized interface surface for future major-version simplification.  
   Files: `api.py`, `interface.py`, `__init__.py`  
   Impact: **medium**  
   Behavior-changing: **yes** (if trimmed, major-version only).

**Bottom line:** ship **after fixing iterator pagination/count correctness**; the rest are quality/security-hardening items worth addressing pre-publish if bandwidth allows, but not release blockers once count semantics are correct.
