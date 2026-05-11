# `envoy.dependency.check` — review status

_Update to [`REVIEW.md`](./REVIEW.md), generated 2026-05-11. The original
report is preserved verbatim; this file tracks what landed where._

## Summary

Every actionable finding from the review is now resolved on `main`.
Two items were intentionally dropped per maintainer triage (see below).

## Finding → PR map

| Finding | Description | Landed in |
|---|---|---|
| 1.1 | Ghost `AGithubIssueManager` in `__all__` | [#4415](https://github.com/envoyproxy/toolshed/pull/4415) |
| 1.2 / 10.1 | Dead SHA-check trifecta (`check_release_sha`, `dep_release_sha_check`, `preload_release_sha`) | [#4434](https://github.com/envoyproxy/toolshed/pull/4434) |
| 1.4 | Fail fast on missing GitHub token | [#4440](https://github.com/envoyproxy/toolshed/pull/4440) |
| 2.1 (walrus) | Reuse walrus-bound `newer_release` | [#4448](https://github.com/envoyproxy/toolshed/pull/4448) |
| 2.2 | `cache=True` on `has_recent_commits` | [#4448](https://github.com/envoyproxy/toolshed/pull/4448) |
| 2.3 | `raise e` → bare `raise` | [#4448](https://github.com/envoyproxy/toolshed/pull/4448) |
| 3.1 | `cache=True` on `release_date_mismatch` / `release_sha_mismatch` | [#4448](https://github.com/envoyproxy/toolshed/pull/4448) |
| 4.1 | `raise_for_status()` on SHA download | [#4443](https://github.com/envoyproxy/toolshed/pull/4443) |
| 4.2 | Implement missing-label `--fix` behaviour | [#4458](https://github.com/envoyproxy/toolshed/pull/4458) |
| 5.1 | `aiohttp.ClientTimeout` on `ClientSession` | [#4443](https://github.com/envoyproxy/toolshed/pull/4443) |
| 5.2 | `User-Agent` header on `ClientSession` | [#4443](https://github.com/envoyproxy/toolshed/pull/4443) |
| 5.3 | Explicit `GITHUB_API_URL` constant | [#4443](https://github.com/envoyproxy/toolshed/pull/4443) |
| 6.1 | `OSError` → `GithubTokenError` on token file read | [#4443](https://github.com/envoyproxy/toolshed/pull/4443) |
| 7.1 | Promote `urls` / `sha256` to required TypedDict fields | [#4444](https://github.com/envoyproxy/toolshed/pull/4444) |
| 7.2 | Missing return-type annotations | [#4448](https://github.com/envoyproxy/toolshed/pull/4448) |
| 7.3 | `# type: ignore` codes / removals | [#4448](https://github.com/envoyproxy/toolshed/pull/4448) |
| 8.1 | Lazy `%`-style `logger.debug` | [#4443](https://github.com/envoyproxy/toolshed/pull/4443) / [#4448](https://github.com/envoyproxy/toolshed/pull/4448) |
| 8.2 | Typos (`shoudl`, `depdendency`) | [#4415](https://github.com/envoyproxy/toolshed/pull/4415) |
| 9.1 | Test patching wrong property | obviated by [#4434](https://github.com/envoyproxy/toolshed/pull/4434) |
| 9.2 | Coverage for `_no_dep_issues` exclusion branch | [#4454](https://github.com/envoyproxy/toolshed/pull/4454) |
| 9.3 | Brittle `MagicMock.__len__` assertion | [#4454](https://github.com/envoyproxy/toolshed/pull/4454) |
| 10.2 | Untracked TODOs triaged | [#4458](https://github.com/envoyproxy/toolshed/pull/4458) |
| 11.1 | Decouple `NO_ISSUE_DEPENDENCIES` / `GITHUB_REPO_LOCATION` / `LABELS` from abstract layer | [#4465](https://github.com/envoyproxy/toolshed/pull/4465) |
| 11.2 | Pre-flight schema validation + `DependencyMetadataError` | [#4444](https://github.com/envoyproxy/toolshed/pull/4444) |
| 12.1 | Flesh out `README.rst` | [#4458](https://github.com/envoyproxy/toolshed/pull/4458) |
| 12.2 | Class docstrings on concrete classes | [#4458](https://github.com/envoyproxy/toolshed/pull/4458) |
| 12.3 | Fix `tagged` docstring | [#4458](https://github.com/envoyproxy/toolshed/pull/4458) |

## Explicitly dropped per maintainer triage

- **1.3** — pass-body concrete classes & `super()`-only overrides.
  Not convinced anything to clean.
- **2.1 (broader)** — narrowed to just the walrus reuse case.
  Repeatedly awaiting cached `async_property`s is fine; only the case
  where the value is *already bound* is a problem.
