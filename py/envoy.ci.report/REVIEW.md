# `envoy.ci.report` — code review

_Generated 2026-05-10. Follow-up to the initial packaging cleanup pass (`py/envoy.ci.report: Cleanup #4421`)._

## Summary

`envoy.ci.report` is a focused CLI tool that walks the GitHub Actions API for the
`envoyproxy/envoy` repository, downloads per-run environment artifacts, correlates
workflow runs with CI request events, and renders either a JSON or Markdown summary.
Its overall shape is reasonable (Runner → abstract layer → interface layer), but
several areas need attention: the concrete-subclass layer adds no value and exists
only to satisfy the `abstracts` framework; there is an async-correctness bug in the
artifact-fetch pipeline where a walrus-operator check tests a coroutine object
(always truthy) instead of its awaited result; all GitHub URLs in the Markdown
formatter are hard-coded to `envoyproxy/envoy` and ignore the `--repo` flag; the
`typing.py` `CIRequestDict.workflows` field is typed incorrectly (`list` instead of
`dict`); error handling around the direct artifact-download path is narrower than it
needs to be; and the test suite tests implementation detail rather than observable
behaviour.

---

## Findings

### 1. Architectural / API-surface smells

#### 1.1 Empty pass-through concrete classes serve no purpose
- **Where**: [`py/envoy.ci.report/envoy/ci/report/runner.py:L9-L14`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/runner.py#L9-L14), [`py/envoy.ci.report/envoy/ci/report/ci.py:L1-L9`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/ci.py#L1-L9)
- **What**: `JSONFormat`, `MarkdownFormat`, `StatusFilter`, `CreationTimeFilter` (in `runner.py`) and `CIRuns` (in `ci.py`) are all empty `pass` bodies. They inherit from their abstract counterparts and add absolutely nothing.
- **Why it matters**: Every call site in `runner.py` still references these thin wrappers; the `ci.py` module exists solely to export a no-op subclass. Readers spend time looking for override logic that does not exist.
- **Suggested fix**: Collapse each empty concrete class into a type alias (`JSONFormat = abstract.AJSONFormat`) or, if the `abstracts` framework requires concrete classes, add a brief comment explaining why the shell exists. For `CIRuns`, consider inlining the `@abstracts.implementer` decorator directly on `ACIRuns` and removing `ci.py` entirely.
- **Effort**: S
- **Risk**: low

#### 1.2 `AFormat.__call__` indirection mismatches the `IFormat` interface
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/format.py:L12-L14`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L12-L14), [`py/envoy.ci.report/envoy/ci/report/interface.py:L23-L27`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/interface.py#L23-L27)
- **What**: `AFormat.__call__` simply delegates to `self.out(data)`. `IFormat` only declares `out`, so an `IFormat` implementor that bypasses `AFormat` would not be callable. The `run()` method calls `self.format(...)` (using `__call__`), but the public contract (`IFormat`) provides no guarantee that `__call__` exists.
- **Why it matters**: A future format class that implements `IFormat` directly (not via `AFormat`) would pass interface checks but silently break the runner.
- **Suggested fix**: Either expose `__call__` on `IFormat` as well, or change the runner to call `self.format.out(...)` and drop `AFormat.__call__`.
- **Effort**: S
- **Risk**: low

#### 1.3 `fetch_check` and `fetch_request_env` are public but exclusively internal
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L129-L181`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L129-L181)
- **What**: `fetch_check`, `fetch_request_env`, `fetch_requests`, and `parse_env` are public methods but are only ever called from private helpers (`_check_run_fetches`, `_env_fetches`).
- **Why it matters**: Exposing implementation helpers as public API freezes their signatures and makes the class surface larger than necessary.
- **Suggested fix**: Rename to `_fetch_check`, `_fetch_request_env`, `_fetch_requests`, `_parse_env` to signal they are internal. Tests will need to be updated accordingly.
- **Effort**: S
- **Risk**: low

#### 1.4 `github_headers` leaks through multiple abstraction layers
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L72-L73`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L72-L73)
- **What**: `self.repo.github.api.oauth_token` — four levels of chaining — is used to build an `Authorization` header for a raw `aiohttp` call that bypasses the `gidgethub`/`aio.api.github` abstraction entirely.
- **Why it matters**: This tight coupling means `ACIRuns` knows the internal attribute layout of `IGithubAPI.api`. If that layout changes, `ACIRuns` silently breaks. The OAuth token is also duplicated (once in gidgethub's internal state, once in the manually constructed header).
- **Suggested fix**: Add an `authorized_get(url)` helper to the repo or session wrapper, or pass the token through the existing `gidgethub` session mechanism for artifact downloads.
- **Effort**: M
- **Risk**: medium

---

### 2. Async correctness

#### 2.1 Walrus-operator condition in `_env_fetches` is always `True`
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L193-L199`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L193-L199)
- **What**:
  ```python
  if fetch_request := self.fetch_request_env(wf, sha, event):
      yield fetch_request
  ```
  `fetch_request_env` is `async def`, so calling it *without* `await` creates a coroutine object. Coroutine objects are unconditionally truthy. The `if` branch is **never False**; the filter is a no-op.
- **Why it matters**: The intent was presumably to avoid yielding to `concurrent()` when no artifact URL exists (i.e., when `fetch_request_env` would return `None` after being awaited). Instead, a coroutine is always created and yielded, adding load even for runs with no artifact. This also produces an inconsistency: `_check_run_fetches` unconditionally yields `self.fetch_check(...)` (correct), while `_env_fetches` *appears* to conditionally yield but doesn't (incorrect).
- **Suggested fix**: Remove the `if` guard and always yield the coroutine — the downstream `if not result: continue` in `envs` already handles `None` returns:
  ```python
  for wf in wfids:
      yield self.fetch_request_env(wf, sha, event)
  ```
- **Effort**: S
- **Risk**: low

#### 2.2 `datetime.utcnow()` and `datetime.utcfromtimestamp()` are deprecated since Python 3.12
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/filters.py:L48`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/filters.py#L48), [`py/envoy.ci.report/envoy/ci/report/abstract/format.py:L63`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L63)
- **What**: Both `datetime.utcnow()` and `datetime.utcfromtimestamp(...)` return *naive* `datetime` objects assumed to represent UTC. Both are deprecated in Python 3.12+ (the package's declared minimum).
- **Why it matters**: The deprecation warning will surface in user environments. More importantly, the produced `datetime` objects lack `tzinfo`, making comparisons with aware datetimes ambiguous and the Markdown output timestamp missing a timezone suffix.
- **Suggested fix**:
  - `filters.py`: `datetime.now(timezone.utc)` (add `from datetime import timezone`)
  - `format.py`: `datetime.fromtimestamp(int(request["started"]), tz=timezone.utc).isoformat()`
- **Effort**: S
- **Risk**: low

#### 2.3 Unbounded concurrency in `check_runs` and `envs`
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L47-L69`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L47-L69)
- **What**: Both `check_runs` and `envs` pass entire async iterables to `concurrent()` with no concurrency cap. For a busy repository this can mean hundreds of simultaneous outbound HTTPS connections.
- **Why it matters**: GitHub rate-limits by the minute; a burst of hundreds of requests will exhaust the quota immediately and could get the token flagged. The host network and file-descriptor limits are also under pressure.
- **Suggested fix**: Pass a `limit=` argument to `concurrent()` if the framework supports it, or use `asyncio.Semaphore` to cap inflight requests to a configurable bound (default ~20).
- **Effort**: M
- **Risk**: medium

---

### 3. GitHub API / HTTP I/O

#### 3.1 Markdown output URLs are hard-coded to `envoyproxy/envoy`, ignoring `--repo`
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/format.py:L37-L38`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L37-L38), [L65-L68](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L65-L68)
- **What**: Every commit URL, event URL, and workflow URL is formed with a literal `"https://github.com/envoyproxy/envoy/..."` string. The `--repo` CLI argument (which defaults to `ENVOY_REPO`) is only used for API calls, never for link generation.
- **Why it matters**: Passing `--repo someorg/somerepo` produces API results for the correct repo but Markdown links all point to the wrong repo. The formatter is completely unusable for any fork or alternative repo.
- **Suggested fix**: Pass the repo name (or the full base URL) as a constructor argument to `AMarkdownFormat` (e.g., `AMarkdownFormat(repo_name)`) and build URLs from it. The runner already has `self.repo_name`.
- **Effort**: S
- **Risk**: low

#### 3.2 `request.yml` workflow name is hard-coded in the fetch URL
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L20-L21`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L20-L21)
- **What**: `URL_GH_REPO_ACTIONS_REQUEST = "actions/workflows/request.yml/runs?head_sha={sha}"` — the workflow file name `request.yml` is baked in.
- **Why it matters**: Any project that adopts this tool without Envoy's specific `request.yml` workflow gets no request-level data. The tool silently produces empty output instead of an explanatory error.
- **Suggested fix**: Expose `--request-workflow` as a CLI argument defaulting to `"request.yml"`, inject it into `ACIRuns`, and use it when building the URL.
- **Effort**: S
- **Risk**: low

#### 3.3 Direct artifact download bypasses gidgethub rate-limit awareness
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L201-L206`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L201-L206)
- **What**: Artifact ZIP downloads go through a raw `aiohttp.ClientSession.get()` call rather than through `gidgethub`. No `User-Agent` header is set beyond `Authorization`.
- **Why it matters**: GitHub requires `User-Agent` on all API requests. The raw `aiohttp` call also bypasses any rate-limit backoff that `gidgethub` or the `aio.api.github` layer might implement. Additionally, there is no retry logic; a transient 5xx from GitHub silently propagates as an unhandled response status.
- **Suggested fix**: Add `"User-Agent": "envoy.ci.report"` to `github_headers`. Consider routing downloads through the existing `gidgethub` session helper, or at minimum wrap the download in an exponential-backoff retry loop.
- **Effort**: M
- **Risk**: medium

#### 3.4 `_resolve_env_artifact_url` catches `IndexError` but not `KeyError`
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L208-L215`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L208-L215)
- **What**:
  ```python
  return (...["artifacts"][0]["archive_download_url"])
  except IndexError:
      log.warning(...)
  ```
  Only `[0]` can raise `IndexError`. If the GitHub API response omits the `"artifacts"` key entirely (e.g., on a malformed or paginated response), a `KeyError` is raised and propagates uncaught.
- **Why it matters**: An unexpected GitHub API schema change or error response would crash the entire run rather than logging a warning and continuing.
- **Suggested fix**: Broaden the except to `except (IndexError, KeyError)` or validate the structure before indexing.
- **Effort**: S
- **Risk**: low

---

### 4. Report-generation correctness

#### 4.1 `_sorted` raises `ValueError` when a commit has no requests
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L217-L229`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L217-L229)
- **What**: The sort key generator `request["started"] for request in item[1]["requests"].values()` is fed to `min()`/`max()`. If `requests` is empty (possible when `_to_dict` only adds commits that have non-empty request lists, but defensively this can still be reached), `min`/`max` on an empty iterable raises `ValueError`.
- **Why it matters**: A single commit with no matching requests would crash the entire render step after all the expensive API fetches have completed.
- **Suggested fix**: Provide a default: `max(..., default=0)` / `min(..., default=0)`.
- **Effort**: S
- **Risk**: low

#### 4.2 Head commit info is taken from `requests[0]` — ordering-dependent
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L238-L241`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L238-L241)
- **What**:
  ```python
  result[commit]["head"] = dict(
      message=requests[0]["request"]["message"],
      target_branch=requests[0]["request"]["target-branch"])
  ```
  The head metadata is taken from whichever request happens to be first after `_to_list_request` sorts by `started`. If two events for the same commit contain different `message` or `target-branch` values (e.g., from a rebase), the winner is non-deterministic.
- **Why it matters**: The commit message and target branch in the output may silently vary between runs.
- **Suggested fix**: Deduplicate or assert uniformity: if all requests for a commit share the same `message`/`target-branch`, assert that; otherwise, document the precedence rule explicitly.
- **Effort**: S
- **Risk**: low

#### 4.3 `started` field is cast to `int`, truncating sub-second precision
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/format.py:L63`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L63)
- **What**: `datetime.utcfromtimestamp(int(request["started"]))` — the `int()` cast discards fractional seconds. The raw `started` value (a float epoch) is stored as `float` in `CIRequestDict` but truncated on display.
- **Why it matters**: Two events that differ only sub-secondly will sort correctly but display identically. Minor, but surprising.
- **Suggested fix**: Remove the `int()` cast; `datetime.fromtimestamp` accepts a `float` directly.
- **Effort**: S (cosmetic)
- **Risk**: low

---

### 5. Caching / memoisation

#### 5.1 `as_dict` is an uncached `@async_property` — recomputes on every access
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L43-L45`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L43-L45)
- **What**: `as_dict` uses `@async_property` (no `cache=True`), while `check_runs`, `envs`, `shas`, `workflow_requests`, and `workflows` all use `@async_property(cache=True)`. Every access to `as_dict` re-runs `_to_dict()` and `_sorted()`.
- **Why it matters**: In the current call path, `as_dict` is accessed exactly once, so there is no runtime penalty today. However, if a caller accesses `as_dict` twice (e.g., to render both JSON and Markdown), all the assembly work is repeated. The inconsistency is also confusing.
- **Suggested fix**: Use `@async_property(cache=True)` to match the other computed properties, or document the intentional choice.
- **Effort**: S
- **Risk**: low

#### 5.2 `registered_filters` / `registered_formats` type declared as `@property` in abstract but `@cached_property` in concrete
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runner.py:L68-L75`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runner.py#L68-L75), [`py/envoy.ci.report/envoy/ci/report/runner.py:L34-L44`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/runner.py#L34-L44)
- **What**: The abstract class declares them as `@property @abstracts.interfacemethod` (dynamic), but the concrete class uses `@cached_property` (computed once). This is a minor contract mismatch: code that calls `runner.registered_formats` multiple times gets a cached dict in the concrete class but would get a fresh dict from any other implementor.
- **Why it matters**: Low risk for this concrete class, but any test mock or alternative implementation that follows the abstract contract would return a new dict on each call.
- **Suggested fix**: Either declare `cached_property` intent at the interface level (add a comment), or make the abstract class default to `@cached_property` where caching is always correct.
- **Effort**: S
- **Risk**: low

---

### 6. Error handling

#### 6.1 `fetch_check` silently mutates the caller's `info` dict
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L129-L143`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L139-L142)
- **What**:
  ```python
  del info["action"]
  info.pop("advice", None)
  info["external_id"] = check_run["external_id"]
  ```
  The `info` dict is mutated in place. Since `_check_run_fetches` iterates over `data["checks"].items()`, the same underlying `info` dict is referenced from the `envs` cache. Mutating it in `fetch_check` corrupts the cached data.
- **Why it matters**: After the first call to `fetch_check` for a given check run, the `"action"` key is gone from the cached `envs` entry. A second pass over `envs` (e.g., by `_check_run_fetches` called a second time) would fail to find `info["action"]` and skip the entry silently — or `KeyError` if code elsewhere relies on it.
- **Suggested fix**: Work on a copy: `info = dict(info)` at the top of `fetch_check` before mutating.
- **Effort**: S
- **Risk**: medium

#### 6.2 `run()` does not catch `aiohttp.ClientError`
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runner.py:L139-L144`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runner.py#L139-L144)
- **What**: `@runner.catches((gidgethub.GitHubException, KeyboardInterrupt))` handles only GitHub-API exceptions. The direct `aiohttp.ClientSession.get()` call in `_fetch_env_artifact` can raise `aiohttp.ClientError` (connection refused, DNS failure, timeout), which is not caught.
- **Why it matters**: A transient network error during artifact download produces an unhandled exception and a non-zero exit with a raw traceback rather than a clean error message.
- **Suggested fix**: Add `aiohttp.ClientError` to the `catches` tuple, or handle it inside `fetch_request_env`.
- **Effort**: S
- **Risk**: low

---

### 7. Schema / data hygiene for CI inputs

#### 7.1 Magic string `"RUN"` is undocumented
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L189`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L189)
- **What**: `if info["action"] != "RUN":` — `"RUN"` is a bare string with no constant or comment.
- **Why it matters**: It is unclear where this value comes from (it must match the `action` field in the `env.json` artifact), making the code fragile if the artifact schema changes.
- **Suggested fix**: Define `ACTION_RUN = "RUN"` in the constants block at the top of `runs.py` and reference it here.
- **Effort**: S
- **Risk**: low

#### 7.2 `ignored` parameter typed as `dict | None` — too permissive
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L29-L34`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L29-L34), [`py/envoy.ci.report/envoy/ci/report/interface.py:L8-L15`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/interface.py#L8-L15)
- **What**: `ignored: dict | None = None` — the body uses `ignored.get("workflows", [])` and `ignored.get("triggers", [])`, revealing a known shape `dict[str, list[str]]`.
- **Why it matters**: `ignored: dict` accepts any dict, including ones with wrong value types, and type checkers cannot catch mistakes in callers.
- **Suggested fix**: Narrow to `dict[str, list[str]] | None`. Better yet, introduce a small `IgnoredConfig(TypedDict)` with `workflows: list[str]` and `triggers: list[str]`.
- **Effort**: S
- **Risk**: low

#### 7.3 `parse_env` accesses artifact JSON without validation
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L170-L181`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L170-L181)
- **What**: `wfdata["checks"]` and `wfdata["request"]` are accessed directly with no guard. A corrupted or differently-shaped artifact causes an unhandled `KeyError` that propagates out of the concurrent pipeline with minimal context.
- **Why it matters**: CI artifact corruption is a real scenario (interrupted uploads, format changes). The current code turns it into an opaque `KeyError` traceback pointing at a generic expression.
- **Suggested fix**: Validate required keys and raise `RequestArtifactFetchError` with a clear message naming the missing field and the `wfid`.
- **Effort**: S
- **Risk**: low

---

### 8. Logging / observability

#### 8.1 All output goes through `print()` — not redirectable
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/format.py:L25`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L25), [L38](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L38), [L53-L58](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L53-L58), [L68](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L68)
- **What**: Both `AJSONFormat` and `AMarkdownFormat` use bare `print()` calls for all output. There is no way to redirect output to a file or capture it without monkey-patching `sys.stdout`.
- **Why it matters**: The runner provides no `--output` flag. Any integration that wraps this tool and wants to capture output must redirect at the process level. Unit tests must patch `builtins.print`.
- **Suggested fix**: Accept an optional `file` parameter (defaulting to `sys.stdout`) in the format class constructor and pass it to `print(…, file=self.file)`. This mirrors the stdlib convention.
- **Effort**: S
- **Risk**: low

#### 8.2 F-string in `log.warning()` call — should use lazy `%s` formatting
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runs.py:L215`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L215)
- **What**: `log.warning(f"Unable to find request artifact: {wfid}")` — f-strings are evaluated eagerly regardless of the effective log level.
- **Why it matters**: Minor performance issue; also inconsistent with Python logging best practices (use `%s` lazy args).
- **Suggested fix**: `log.warning("Unable to find request artifact: %s", wfid)`
- **Effort**: S (nit)
- **Risk**: low

##### Minor nits
- No debug-level logging at fetch boundaries (starting a fetch, received N workflows, etc.), making it hard to diagnose hangs or slow runs.

---

### 9. Type-annotation correctness

#### 9.1 `CIRequestDict.workflows` has the wrong type
- **Where**: [`py/envoy.ci.report/envoy/ci/report/typing.py:L17-L21`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/typing.py#L17-L21)
- **What**:
  ```python
  class CIRequestDict(TypedDict):
      workflows: list[dict[str, CIWorkflowDict]]
  ```
  The actual structure built in `_to_dict` is a `dict` keyed by workflow run ID (an `int`):
  ```python
  result[commit]["requests"][req_id]["workflows"][request["workflow_id"]] = ...
  ```
  The correct type is `dict[int, CIWorkflowDict]`.
- **Why it matters**: Static type checkers will not flag incorrect accesses like `workflows[0]` (which would fail at runtime) and will miss real type errors in callers.
- **Suggested fix**: Change to `workflows: dict[int, CIWorkflowDict]`.
- **Effort**: S
- **Risk**: low

#### 9.2 Missing return-type annotations on concrete `registered_filters` / `registered_formats`
- **Where**: [`py/envoy.ci.report/envoy/ci/report/runner.py:L34-L44`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/runner.py#L34-L44)
- **What**: Both `registered_filters` and `registered_formats` in `ReportRunner` lack return-type annotations. The abstract base already specifies `-> dict`, but the concrete overrides omit them entirely.
- **Suggested fix**: Add `-> dict[str, type[abstract.AWorkflowFilter]]` and `-> dict[str, type[abstract.AFormat]]` respectively.
- **Effort**: S
- **Risk**: low

#### 9.3 Several private helpers in `AMarkdownFormat` lack all type annotations
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/format.py:L43`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L43), [L61](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/format.py#L61)
- **What**: `_handle_commit_message(self, message)` has no annotation on `message`; `_handle_event(self, request_id, request)` has no annotations on either parameter.
- **Suggested fix**: `message: str`, `request_id: int`, `request: dict` (or the appropriate `TypedDict` variants from `typing.py`).
- **Effort**: S
- **Risk**: low

#### 9.4 `IWorkflowFilter.__init__` takes untyped `args`
- **Where**: [`py/envoy.ci.report/envoy/ci/report/interface.py:L45`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/interface.py#L45)
- **What**: `def __init__(self, args) -> None:` — `args` is unannotated in the interface.
- **Suggested fix**: `args: argparse.Namespace` (matching the concrete implementation).
- **Effort**: S
- **Risk**: low

#### 9.5 `ICIRuns.as_dict` declared as a plain method, implemented as `async_property`
- **Where**: [`py/envoy.ci.report/envoy/ci/report/interface.py:L18-L20`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/interface.py#L18-L20)
- **What**: The interface declares `async def as_dict(self) -> dict:` but `ACIRuns` implements it as `@async_property`, which is accessed as an attribute (`await runs.as_dict`), not called (`await runs.as_dict()`).
- **Why it matters**: A conforming `ICIRuns` implementation could use a real async method, breaking any caller that accesses it as a property.
- **Suggested fix**: Either add the `async_property` decorator to the interface declaration, or restructure so `as_dict` is consistently a callable method throughout.
- **Effort**: S
- **Risk**: low

---

### 10. Testing smells

#### 10.1 Tests assert `call_args` tuples rather than behaviour
- **Where**: Throughout [`py/envoy.ci.report/tests/test_abstract_runs.py`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/tests/test_abstract_runs.py), e.g. [L689-L732](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/tests/test_abstract_runs.py#L689-L732)
- **What**: Most tests pattern-match on `m_method.call_args == [(args,), {}]` rather than asserting on observable output. This makes tests break on refactoring without verifying actual correctness.
- **Why it matters**: A bug that produces the wrong result using the right call sequence will pass all tests. Tests should assert on what the method *returns* or *produces*, not on exactly which internal calls were made.
- **Suggested fix**: Supplement `call_args` assertions with assertions on return values and side-effects. Use `mock.assert_called_once_with(...)` for readability.
- **Effort**: L
- **Risk**: low

#### 10.2 Magic arithmetic in test expectation
- **Where**: [`py/envoy.ci.report/tests/test_abstract_runs.py:L579`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/tests/test_abstract_runs.py#L579)
- **What**: `== [m_fetch.return_value] * (625 - 375)` — the `250` is the product of the `iters` iteration structure (`5^4 / 2`), but it is written as unexplained arithmetic.
- **Why it matters**: The next reader cannot verify the number is correct without re-deriving the combinatorics.
- **Suggested fix**: Assign to a named constant or add a comment: `EXPECTED_FETCHES = 5**4 // 2  # 4 nested iters of 5, skip odd idx3`.
- **Effort**: S
- **Risk**: low

#### 10.3 Commented-out assertion left in test
- **Where**: [`py/envoy.ci.report/tests/test_abstract_runs.py:L852`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/tests/test_abstract_runs.py#L852)
- **What**: `# assert _requests[i].__getitem__.return_value == first_request` — dead code.
- **Suggested fix**: Remove the commented-out line.
- **Effort**: S (nit)
- **Risk**: low

#### 10.4 `_env_fetches` test does not detect the always-true walrus condition (finding 2.1)
- **Where**: [`py/envoy.ci.report/tests/test_abstract_runs.py:L593-L648`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/tests/test_abstract_runs.py#L593-L648)
- **What**: The test mocks `fetch_request_env` (a `MagicMock`, which is truthy), so the walrus-operator bug goes undetected. No test case exercises the scenario where `fetch_request_env` would return `None` (i.e., when no artifact exists) and verifies that the coroutine is not yielded.
- **Suggested fix**: Add a test variant where `fetch_request_env` is an `AsyncMock(return_value=None)` and assert that nothing is yielded. Fix the source code per finding 2.1 first.
- **Effort**: S
- **Risk**: low

##### Minor nits
- No end-to-end test against a recorded (VCR/cassette) GitHub API response; all tests are fully mocked.
- `test_ci.py` and `test_runner.py` each contain a single constructor test — effectively just testing that `@abstracts.implementer` wired up correctly, which the framework itself guarantees.

---

### 11. Dead / duplicated / commented-out code

#### 11.1 Commented-out `--start` / `--end` arguments with outstanding TODO
- **Where**: [`py/envoy.ci.report/envoy/ci/report/abstract/runner.py:L107-L108`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runner.py#L107-L108), [`py/envoy.ci.report/envoy/ci/report/abstract/filters.py:L110-L112`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/filters.py#L110-L112)
- **What**:
  ```python
  # parser.add_argument("--end")
  # parser.add_argument("--start")
  ```
  and
  ```python
  # TODO: allow start/end times to be set directly
  return self.now - timedelta(hours=(24 * 7))
  ```
- **Why it matters**: The TODO is never tracked in a ticket; the commented-out lines are noise for every future reader.
- **Suggested fix**: Either implement the `--start`/`--end` arguments (the filter logic already has most of the time-range infrastructure) or remove the comments and open a GitHub issue instead.
- **Effort**: S
- **Risk**: low

#### 11.2 The entire `_env_fetches` walrus-operator branch is effectively dead
- Already covered in **2.1** above; calling it out as dead-code too.

---

### 12. Documentation

#### 12.1 `README.rst` still contains the wrong description
- **Where**: [`py/envoy.ci.report/README.rst:L4-L5`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/README.rst#L4-L5)
- **What**: The README reads *"Release publishing tool used in Envoy proxy's CI"* — the same text that was cargo-culted from `envoy.distribution.release`. The `setup.cfg` description was corrected to *"CI report tool used in Envoy proxy's CI"* in the initial cleanup PR, but `README.rst` was not updated.
- **Suggested fix**: Update `README.rst` to match `setup.cfg`; consider expanding it with a brief usage example (`envoy.ci.report --format markdown --previous day`).
- **Effort**: S
- **Risk**: low

#### 12.2 No module-level docstrings or public API docstrings
- **Where**: All modules under [`py/envoy.ci.report/envoy/ci/report/`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/), e.g. [`abstract/runs.py:L1`](https://github.com/envoyproxy/toolshed/blob/fa540df8a0befb9bf7fe50a4124d8a78ac444d06/py/envoy.ci.report/envoy/ci/report/abstract/runs.py#L1)
- **What**: Only `ReportRunner` has a class-level docstring. `ACIRuns`, `ACreationTimeFilter`, `AMarkdownFormat`, `AReportRunner`, all interface classes, and all public methods (`parse_env`, `fetch_check`, etc.) are undocumented.
- **Why it matters**: The data pipeline is non-trivial (GitHub API → artifacts → ZIP parsing → dict assembly). A reader must trace the entire call graph to understand what each piece does.
- **Suggested fix**: At minimum, add one-line docstrings to `ACIRuns`, `AMarkdownFormat`, and each of their public methods. Focus on *what* each method returns, not *how*.
- **Effort**: M
- **Risk**: low

---

## Recommended follow-up PRs

| # | Title | Findings | Effort | Risk |
|---|-------|----------|--------|------|
| 1 | **Fix async bug: remove dead walrus-operator filter in `_env_fetches`** | 2.1, 10.4 | S | low |
| 2 | **Fix hard-coded `envoyproxy/envoy` URLs in Markdown formatter** | 3.1 | S | low |
| 3 | **Fix `CIRequestDict.workflows` TypedDict field type** | 9.1 | S | low |
| 4 | **Replace deprecated `datetime.utcnow()` / `utcfromtimestamp()`** | 2.2, 4.3 | S | low |
| 5 | **Harden error handling: `KeyError` in artifact resolution, `aiohttp.ClientError` in runner, mutation in `fetch_check`** | 3.4, 6.1, 6.2 | S | medium |
| 6 | **Add `--request-workflow` CLI flag; extract `ACTION_RUN` constant; narrow `ignored` type** | 3.2, 7.1, 7.2, 7.3 | S | low |
| 7 | **Fix README; add module and public-method docstrings; add `User-Agent` header** | 3.3, 8.1 (partial), 12.1, 12.2 | M | low |
| 8 | **Cap concurrency with a semaphore or `limit=` parameter** | 2.3 | M | medium |
| 9 | **Add complete type annotations** (return types on `registered_*`, `_handle_*` params, `IWorkflowFilter.__init__`, `ICIRuns.as_dict`) | 9.2, 9.3, 9.4, 9.5 | S | low |
| 10 | **Collapse empty pass-through classes; clean up commented-out `--start`/`--end` args** | 1.1, 11.1 | S | low |
