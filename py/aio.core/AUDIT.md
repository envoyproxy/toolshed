# `aio.core` audit against Python 3.12+ stdlib

Audit target: `py/aio.core/aio/core/` at `main` SHA [`4ef90607b906d06de3c9177bd0281e0651859fb8`](https://github.com/envoyproxy/toolshed/tree/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core)

## Scope and method

I treated **in-repo consumers under `py/` as the canonical consumer set**, per the task brief. I read the public package roots, the underlying implementation modules, and the existing `py/aio.core/tests/` test suite, then mapped consumers across the rest of `py/` and compared each public export to the Python 3.12 stdlib.

Two framing conclusions before the per-package detail:

- The user hypothesis was basically right: **most of `aio.core` is defensible**, especially `functional.async_property`, `functional.AwaitableGenerator`, and the core of `tasks.concurrent`.
- The package is also undeniably a **hotch-potch**: `directory`, `dev`, `log`, large parts of `functional`, `subprocess`, and nearly all of `utils` are either generic helpers or wrappers around OS/process/data concerns, not asyncio patterns.

---

## A–D. Subpackage audit

## `dev`

**Tests:** [`py/aio.core/tests/test_dev.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_dev.py)

**Public modules**

- [`debug`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/dev/debug.py#L1-L186) (~186 LOC) — generic debug/trace decorators (`ADebugLogging`, `ATraceLogging`, `ANullLogging`, `logging`) for sync, async, generator, and async-generator callables. **Consumers:** `envoy.code.check` (4 refs).

| Export | LOC | What it does | In-repo consumers | Stdlib 3.12+ comparison | Verdict |
|---|---:|---|---|---|---|
| [`timing`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/dev/perf.py#L6-L18) | 13 | Simple sync decorator around `time.perf_counter()` that prints elapsed time. | **Zero** | Thin wrapper over `time.perf_counter()` + `functools.wraps`; no asyncio value. | **DROP** |

**Subpackage verdict:** **MOVE**. The `debug` module is useful, but it is plain debugging instrumentation, not an asyncio abstraction. Keep the idea if wanted, but not under `aio.*`. `timing` is unused and not worth carrying.

---

## `directory`

**Tests:** [`py/aio.core/tests/test_directory.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_directory.py)

**Public modules**

- [`directory.utils`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/utils.py#L1-L15) (~15 LOC) — `directory_context`, a sync `chdir` context manager. **Consumers:** `envoy.code.check` (1 ref).

| Export | LOC | What it does | In-repo consumers | Stdlib 3.12+ comparison | Verdict |
|---|---:|---|---|---|---|
| [`IDirectoryContext`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/context.py#L11-L23) | 13 | Interface for `.path` plus `in_directory`. | `envoy.code.check` (8 refs) | Generic filesystem/CWD protocol; no asyncio content. | **MOVE** |
| [`ADirectoryContext`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/context.py#L27-L41) | 15 | Cached `pathlib.Path` plus `directory_context`. | `envoy.code.check` (10 refs) | Thin wrapper over `pathlib.Path` + custom `os.chdir` context manager. | **MOVE** |
| [`ADirectoryFileFinder`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/abstract/directory.py#L25-L70) | 46 | Blocking grep-based file finder; intended to run in an executor. | **Zero** | Shells out to `grep`; public only by accident. | **DROP** |
| [`AGitDirectoryFileFinder`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/abstract/directory.py#L75-L118) | 44 | Git-aware file finder parsing `git ls-files --eol`. | **Zero** | No stdlib git equivalent, but still internal plumbing. | **DROP** |
| [`ADirectory`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/abstract/directory.py#L122-L290) | 169 | Async directory abstraction with cached `files`, batched grep, and executor-backed search. | `dependatool` (3), `envoy.base.utils` (5), `envoy.code.check` (3) | For plain filesystem walking, `pathlib.Path.walk()` / `Path.rglob()` + `asyncio.to_thread()` now cover the Python part cleanly; the grep/git shelling is the real value. | **MOVE** |
| [`AGitDirectory`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/abstract/directory.py#L293-L415) | 123 | `git grep`/`git diff`/`git ls-files` flavored `ADirectory`. | **Zero direct consumers** (used via `GitDirectory`) | No stdlib git abstraction; useful, but this is repo/fs tooling, not asyncio. | **MOVE** |
| [`Directory`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/directory.py#L7-L11) | 5 | Concrete plain-directory leaf. | `envoy.code.check` (2) | Could be re-expressed with `pathlib.Path.walk()` + `asyncio.to_thread()` if grep-shelling is not needed. | **MOVE** |
| [`DirectoryFileFinder`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/directory.py#L14-L15) | 2 | Concrete leaf for `ADirectoryFileFinder`. | **Zero** | Implementation detail only. | **DROP** |
| [`GitDirectory`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/directory.py#L22-L26) | 5 | Concrete git-directory leaf. | `dependatool` (2), `envoy.base.utils` (2), `envoy.code.check` (2) | No stdlib replacement for git behavior; still mispackaged under `aio.*`. | **MOVE** |
| [`GitDirectoryFileFinder`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/directory/directory.py#L18-L19) | 2 | Concrete leaf for `AGitDirectoryFileFinder`. | **Zero** | Implementation detail only. | **DROP** |

**Subpackage verdict:** **MOVE**. This is productive code, but it is filesystem/git tooling with async wrappers, not an asyncio pattern library. The public API is also too wide: the finder classes should not be public.

---

## `event`

**Tests:** [`test_event_loader.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_event_loader.py), [`test_event_reactive.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_event_reactive.py), [`test_event_executive.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_event_executive.py)

| Export | LOC | What it does | In-repo consumers | Stdlib 3.12+ comparison | Verdict |
|---|---:|---|---|---|---|
| [`ILoader`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/event/loader.py#L9-L85) | 77 | Protocol for cooperative “loading / loaded” state. | `envoy.dependency.check` (1) | Built from stdlib `asyncio.Event`; no direct stdlib single-flight primitive. | **KEEP** |
| [`ALoader`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/event/loader.py#L89-L127) | 39 | Two-`Event` implementation of the loader protocol. | **Zero direct consumers** | Still useful as the implementation behind `Loader`, but the public ABC is not pulling extra weight. | **KEEP-BUT-MODERNISE** |
| [`Loader`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/event/loader.py#L130-L132) | 2 | Concrete leaf used by `async_property` cooperative caching. | `envoy.dependency.check` (1) | No stdlib equivalent; this is a legitimate tiny helper. | **KEEP** |
| [`IReactive`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/event/reactive.py#L9-L22) | 14 | Protocol for `.loop` and `.pool`. | `aio.run.runner` (2), `envoy.code.check` (1), `envoy.dependency.check` (5) | Wraps stdlib `asyncio.AbstractEventLoop` and `concurrent.futures.Executor`. | **KEEP-BUT-MODERNISE** |
| [`AReactive`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/event/reactive.py#L25-L40) | 16 | Default `.loop` and `.pool` mixin. | `aio.run.runner` (2), `envoy.code.check` (1), `envoy.dependency.check` (2) | Uses deprecated-ish `asyncio.get_event_loop()` and defaults to `ProcessPoolExecutor()` even for shell-heavy IO cases. | **KEEP-BUT-MODERNISE** |
| [`IExecutive`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/event/executive.py#L12-L34) | 23 | Protocol for executor-backed `execute()` / `execute_in_batches()`. | `aio.api.nist` (1), `envoy.base.utils` (1), `envoy.code.check` (1), `envoy.dependency.check` (1) | General wrapper over `loop.run_in_executor()` plus batching. | **KEEP-BUT-MODERNISE** |
| [`AExecutive`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/event/executive.py#L38-L87) | 50 | Concrete mixin using `run_in_executor` and `tasks.concurrent`. | `aio.api.nist` (1), `dependatool` (1), `envoy.base.utils` (1), `envoy.code.check` (1), `envoy.dependency.check` (1) | Stdlib gives the primitives (`run_in_executor`, `asyncio.to_thread`, executors), but not this mixin. Also has a latent kwargs bug in `execute()`. | **KEEP-BUT-MODERNISE** |

**Subpackage verdict:** **KEEP-BUT-MODERNISE**. This is one of the defensible bits. `Loader` is still useful. `Reactive`/`Executive` still earn their place, but they need a 3.12 pass: `get_running_loop()`, sane executor defaults, and a fix for `execute(..., **kwargs)`.

---

## `functional`

**Tests:** [`py/aio.core/tests/test_functional.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_functional.py)

**Public modules**

- [`collections`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/collections.py#L1-L169) (~169 LOC) — async collection helpers plus `CollectionQuery` / `QueryDict`. **Consumers as module:** zero.
- [`exceptions`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/exceptions.py#L1-L17) (~17 LOC) — `CollectionQueryError`, `TypeCastingError`, `BatchedJobsError`. **Consumers as module:** `envoy.code.check` (10 refs).
- [`utils`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/utils.py#L1-L129) (~129 LOC) — misc sync helpers (`typed`, `nested`, `batches`, `batch_jobs`, etc.). **Consumers as module:** `aio.api.nist` (2 refs).

| Export | LOC | What it does | In-repo consumers | Stdlib 3.12+ comparison | Verdict |
|---|---:|---|---|---|---|
| [`async_property`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/decorators.py#L21-L152) | 132 | Async descriptor with optional caching and cooperative single-flight loading per instance. | `aio.api.github` (7), `aio.api.nist` (1), `dependatool` (5), `envoy.base.utils` (5), `envoy.ci.report` (8), `envoy.code.check` (55), `envoy.dependency.check` (24), `envoy.distribution.release` (2), `envoy.distribution.repo` (11), `envoy.github.abstract` (17), `envoy.github.release` (17) | There is still no stdlib async cached property. This is real value. | **KEEP** |
| [`AwaitableGenerator`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/generator.py#L13-L83) | 71 | Makes an async iterable both awaitable (collect) and async-iterable (stream). | `envoy.code.check` (2), `envoy.dependency.check` (1), `envoy.github.abstract` (1) | No direct stdlib equivalent; `async for` and list/set comprehensions cover parts, not the dual API. | **KEEP** |
| [`async_iterator`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/collections.py#L10-L28) | 19 | Predicate/result adapter over an async iterable. | **Zero** | Mostly replaceable by inline async generator expressions/comprehensions. | **DROP** |
| [`async_list`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/collections.py#L31-L45) | 15 | Collect async iterable to `list`. | **Zero** | `[x async for x in gen]` is the modern stdlib spell. | **DROP** |
| [`async_set`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/collections.py#L48-L60) | 13 | Collect async iterable to `set`. | **Zero** | `{x async for x in gen}` is the modern stdlib spell. | **DROP** |
| [`async_map`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/process.py#L6-L25) | 20 | Eager executor-backed async mapping over a sync iterable. | **Zero** | `asyncio.to_thread()`, `loop.run_in_executor()`, and `asyncio.as_completed()` cover this more transparently now. | **DROP** |
| [`batches`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/utils.py#L100-L109) | 10 | Fixed-size batching helper. | **Zero** | Direct overlap with `itertools.batched()` in Python 3.12. | **DROP** |
| [`batch_jobs`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/utils.py#L112-L129) | 18 | CPU-count-based batching heuristic. | **Zero** | No exact stdlib helper, but it is internal policy, not a public asyncio primitive. | **DROP** |
| [`CollectionQuery`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/collections.py#L86-L146) | 61 | Path-query helper for nested mappings/lists. | **Zero** | No stdlib equivalent, but also not remotely asyncio-specific. | **MOVE** |
| [`QueryDict`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/collections.py#L149-L165) | 17 | Preconfigured multi-query extractor. | `aio.api.nist` (3) | Still useful, but this is generic data-query code, not async code. | **MOVE** |
| [`qdict`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/collections.py#L168-L169) | 2 | Factory for `QueryDict`. | `aio.api.nist` (1), `envoy.dependency.check` (1) | Useful sugar for the same generic query DSL. | **MOVE** |
| [`maybe_awaitable`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/utils.py#L23-L41) | 19 | Makes a plain value awaitable. | **Zero** | No exact stdlib `wrap_value()` helper, but no consumers. | **DROP** |
| [`maybe_coro`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/utils.py#L44-L69) | 26 | Wraps sync or async callable into a coroutine function. | **Zero** | Thin wrapper over `inspect.iscoroutinefunction` + local `async def`. | **DROP** |
| [`nested`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/utils.py#L72-L78) | 7 | Tiny `contextlib.ExitStack` wrapper. | **Zero** | Stdlib `contextlib.ExitStack` already is the abstraction. | **DROP** |
| [`typed`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/utils.py#L85-L96) | 12 | Runtime structural type assertion via `trycast`. | **Zero** | Stdlib typing does not fully replace runtime shape checks; still not an asyncio helper and has no canonical consumers. | **DROP** |
| [`buffered`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/__init__.py#L23-L42) | n/a | Exported in `__all__`, but not imported or defined. Stale public API entry. | **Zero** | Pure dead weight. | **DROP** |

**Subpackage verdict:** **split it**. `async_property` and `AwaitableGenerator` are worth keeping. `QueryDict`/`qdict` are fine code but belong somewhere generic, not under `aio`. A lot of the rest is either internal plumbing or now-cleaner stdlib in 3.12.

---

## `log`

**Tests:** [`py/aio.core/tests/test_log.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_log.py)

| Export | LOC | What it does | In-repo consumers | Stdlib 3.12+ comparison | Verdict |
|---|---:|---|---|---|---|
| [`QueueHandler`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/log/logging.py#L11-L19) | 9 | Subclass of stdlib `logging.handlers.QueueHandler` that re-raises `asyncio.CancelledError`. | **Zero direct consumers** | The CancelledError behavior is the only real custom value; otherwise it is stdlib. | **DROP** |
| [`QueueLogger`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/log/logging.py#L22-L88) | 67 | Convenience wrapper assembling `QueueHandler` + `QueueListener` + `SimpleQueue`. | `aio.run.runner` (1) | In 3.12 the stdlib `logging.handlers.QueueHandler` / `QueueListener` combo is already the clean way to do this. This helper is mostly orchestration. | **DEPRECATE** |

**Subpackage verdict:** **DEPRECATE**. The one consumer can be migrated to stdlib logging handlers directly. This code is also generic logging code, not asyncio code.

**Before / after sketch**

```python
# today
logger = QueueLogger(logger).start()

# stdlib 3.12+
queue = queue.SimpleQueue()
queue_handler = logging.handlers.QueueHandler(queue)
listener = logging.handlers.QueueListener(queue, *logger.handlers)
logger.handlers = [queue_handler]
listener.start()
```

---

## `pipe`

**Tests:** [`py/aio.core/tests/test_abstract_pipe.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_abstract_pipe.py)

**Public modules**

- [`abstract`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/abstract/__init__.py#L1-L7) (~7 LOC) — module re-export for `AProcessProtocol` and `AStdinStdoutProcessor`. **Consumers as module:** zero.
- [`interface`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/interface.py#L1-L43) (~43 LOC) — protocol types, including internal `IProcessor`. **Consumers as module:** zero.
- [`pipe`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/pipe.py#L1-L9) (~9 LOC) — concrete leaf module. **Consumers as module:** zero.

| Export | LOC | What it does | In-repo consumers | Stdlib 3.12+ comparison | Verdict |
|---|---:|---|---|---|---|
| [`AProcessProtocol`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/abstract/pipe.py#L15-L33) | 19 | Abstract async protocol wrapper over `process(request)`. | `aio.api.bazel` (1) | No direct stdlib replacement; thin but acceptable. | **KEEP-BUT-MODERNISE** |
| [`IProcessProtocol`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/interface.py#L23-L43) | 21 | Protocol for the request handler. | `aio.api.bazel` (3) | Fine protocol wrapper over stdlib stream processing. | **KEEP-BUT-MODERNISE** |
| [`AStdinStdoutProcessor`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/abstract/pipe.py#L37-L188) | 152 | Three-task stdin/stdout processor using queues and stream wiring. | **Zero direct consumers** (used via concrete leaf) | Still useful, but implemented with deprecated/private asyncio internals (`get_event_loop`, `asyncio.streams.FlowControlMixin`, direct `StreamWriter` construction, `gather/create_task` instead of `TaskGroup`). | **KEEP-BUT-MODERNISE** |
| [`IStdinStdoutProcessor`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/interface.py#L16-L20) | 5 | Interface for stdin/stdout processors. | `aio.api.bazel` (2) | Fine, but only as part of this niche pipe stack. | **KEEP-BUT-MODERNISE** |
| [`StdinStdoutProcessor`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/pipe.py#L8-L9) | 2 | Concrete leaf processor. | `aio.api.bazel` (1) | No stdlib equivalent at this exact level. | **KEEP-BUT-MODERNISE** |

**Subpackage verdict:** **KEEP-BUT-MODERNISE**. The abstraction is still useful for `aio.api.bazel`, but the implementation is standing on private asyncio internals and should be cleaned up before Python moves them again.

---

## `subprocess`

**Tests:** [`test_aio.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_aio.py), [`test_subprocess_handler.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_subprocess_handler.py)

**Public modules**

- [`exceptions`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/subprocess/exceptions.py#L1-L8) (~8 LOC) — `RunError`, `OSCommandError`. **Consumers as module:** `envoy.code.check` (11 refs).

| Export | LOC | What it does | In-repo consumers | Stdlib 3.12+ comparison | Verdict |
|---|---:|---|---|---|---|
| [`AsyncSubprocess`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/subprocess/async_subprocess.py#L12-L99) | 88 | Async wrapper around `subprocess.run`; parallel variant uses `ensure_future` + executor pool. | **Zero** | Modern stdlib has `asyncio.create_subprocess_exec()` / `create_subprocess_shell()`; this wrapper adds little. | **DROP** |
| [`run`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/subprocess/async_subprocess.py#L115-L115) | 1 | Alias for `AsyncSubprocess.run`. | **Zero** | Covered by the same stdlib subprocess primitives. | **DROP** |
| [`parallel`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/subprocess/async_subprocess.py#L102-L112) | 11 | `AwaitableGenerator` wrapper around `AsyncSubprocess.parallel`. | **Zero** | `asyncio.TaskGroup` / `asyncio.as_completed` + native async subprocesses make this redundant. | **DROP** |
| [`ISubprocessHandler`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/subprocess/handler.py#L15-L78) | 64 | Protocol for cwd-aware subprocess handler objects. | `envoy.code.check` (4) | Useful abstraction, but this is generic subprocess tooling, not asyncio. | **MOVE** |
| [`ASubprocessHandler`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/subprocess/handler.py#L82-L180) | 99 | Base class for sync subprocess handlers with result/error hooks. | `envoy.code.check` (4) | Thin wrapper around `subprocess.run()` plus cwd defaults. No asyncio at all. | **MOVE** |

**Subpackage verdict:** **split and shrink**. Drop the unused async wrapper layer; move the handler abstraction somewhere generic if it still earns its keep for `envoy.code.check`.

---

## `tasks`

**Tests:** [`py/aio.core/tests/test_task.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_task.py)

| Export | LOC | What it does | In-repo consumers | Stdlib 3.12+ comparison | Verdict |
|---|---:|---|---|---|---|
| [`Concurrent`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/tasks/tasks.py#L19-L447) | 429 | Lazy concurrency engine for sync/async providers of awaitables, with limit, cancellation, and typed error wrapping. | **Zero direct consumers** | Closest stdlib overlap is `asyncio.as_completed()` plus `asyncio.TaskGroup`, but neither provides this exact lazy + limited + result-streaming combo. | **KEEP-BUT-MODERNISE** |
| [`concurrent`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/tasks/tasks.py#L450-L460) | 11 | `AwaitableGenerator` wrapper over `Concurrent`. | `aio.api.github` (1), `aio.api.nist` (1), `envoy.base.utils` (1), `envoy.ci.report` (3), `envoy.github.abstract` (1) | Still useful; stdlib does not quite replace it. Implementation could use `TaskGroup`/clearer cancellation paths. | **KEEP-BUT-MODERNISE** |
| [`inflate`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/tasks/tasks.py#L463-L500) | 38 | Preloads groups of awaitables per object, then yields the original objects. | `envoy.code.check` (1), `envoy.dependency.check` (3) | Mostly convenience over `asyncio.gather()` / `TaskGroup` and has awkward exception handling. | **DEPRECATE** |
| [`ConcurrentError`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/tasks/exceptions.py#L2-L5) | 4 | Base error for bad inputs/scheduling. | `envoy.dependency.check` (8), `envoy.github.abstract` (3), `envoy.github.release` (2) | Extra semantic value beyond raw stdlib exceptions. | **KEEP** |
| [`ConcurrentIteratorError`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/tasks/exceptions.py#L8-L11) | 4 | Distinguishes provider/iteration failure from task failure. | `envoy.github.abstract` (5) | Stdlib has no equivalent typed distinction. | **KEEP** |
| [`ConcurrentExecutionError`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/tasks/exceptions.py#L14-L17) | 4 | Distinguishes task-execution failure. | `envoy.base.utils` (1) | Stdlib has no equivalent typed distinction. | **KEEP** |

**Subpackage verdict:** **KEEP-BUT-MODERNISE**. This is another defensible core. `concurrent()` still does something stdlib does not do neatly. `inflate()` is the outlier: not much surface value, not many consumers, and easy enough to replace inline.

**Before / after sketch**

```python
# today
async for obj in inflate(items, lambda o: (o.foo, o.bar), limit=8):
    ...

# stdlib 3.12+
async with asyncio.TaskGroup() as tg:
    for obj in items:
        tg.create_task(obj.foo)
        tg.create_task(obj.bar)
for obj in items:
    ...
```

---

## `utils`

**Tests:** [`py/aio.core/tests/test_utils.py`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/tests/test_utils.py)

| Export | LOC | What it does | In-repo consumers | Stdlib 3.12+ comparison | Verdict |
|---|---:|---|---|---|---|
| [`Captured`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/context.py#L7-L19) | 13 | Tiny holder for warnings + result. | **Zero** | Thin convenience wrapper around stdlib warnings capture. | **DROP** |
| [`captured_warnings`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/context.py#L22-L27) | 6 | Wraps `warnings.catch_warnings(record=True)` and yields a `Captured`. | `aio.api.bazel` (1) | Stdlib `warnings.catch_warnings(record=True)` already does the real work. | **DEPRECATE** |
| [`dottedname`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/resolve.py#L3-L38) | 36 | Resolve dotted names via `__import__` and attribute traversal. | **Zero** | `importlib.import_module()` is the modern stdlib way; this implementation is pre-`importlib` style. | **DEPRECATE** |
| [`dottedname_resolve`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/__init__.py#L15-L15) | 1 | Alias for `dottedname`. | `aio.api.bazel` (1) | Same modern replacement as `dottedname`. | **DEPRECATE** |
| [`ellipsize`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/data.py#L19-L24) | 6 | Character-count truncation with `...`. | **Zero** | `textwrap.shorten()` is close enough for most prose use; either way this has no canonical consumers. | **DROP** |
| [`extract`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/data.py#L27-L39) | 13 | Extract one or more tarballs into a path. | **Zero** | Stdlib `tarfile` already does this; current helper is also security-sensitive (`extractall()` without explicit `filter=`). | **DROP** |
| [`ExtractError`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/exceptions.py#L3-L4) | 2 | Exception for `extract`. | **Zero** | Dead if `extract` goes. | **DROP** |
| [`from_json`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/data.py#L42-L50) | 9 | Load JSON file, optionally runtime-check type. | `envoy.code.check` (1) | Thin wrapper over `pathlib.Path.read_text()` + `json.loads()`. | **DEPRECATE** |
| [`from_yaml`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/data.py#L53-L61) | 9 | Load YAML file, optionally runtime-check type. | `dependatool` (1), `envoy.code.check` (2) | No stdlib YAML parser exists, so the YAML dependency is still justified; still not an asyncio helper. | **MOVE** |
| [`is_sha`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/data.py#L64-L71) | 8 | Test for 40-char hex git SHA. | **Zero** | Trivial generic helper. | **DROP** |
| [`is_tarlike`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/data.py#L74-L81) | 8 | Extension-based tar-ish check. | **Zero** | Trivial generic helper. | **DROP** |
| [`to_yaml`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/data.py#L84-L93) | 10 | Dump YAML to a path. | **Zero** | Generic serialization helper; no asyncio content and no canonical consumers. | **DROP** |

**Subpackage verdict:** **mostly DROP/DEPRECATE/MOVE**. This is the clearest kitchen-sink area in `aio.core`.

**Before / after sketches**

```python
# captured_warnings today
with captured_warnings() as captured:
    ...

# stdlib 3.12+
with warnings.catch_warnings(record=True) as captured:
    ...
```

```python
# dottedname today
obj = dottedname_resolve("pkg.mod.symbol")

# stdlib 3.12+
module_name, _, attr = "pkg.mod.symbol".rpartition(".")
obj = getattr(importlib.import_module(module_name), attr)
```

```python
# from_json today
config = from_json(path, type=MyType)

# stdlib 3.12+
config = json.loads(pathlib.Path(path).read_text())
```

---

## E. Cross-cutting findings

1. **`aio.core` already assumes a modern Python baseline in places, but not consistently modern stdlib usage.**
   - `asyncio.get_event_loop()` is still used in [`event/reactive.py#L29-L40`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/event/reactive.py#L29-L40) and [`pipe/abstract/pipe.py#L88-L90`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/abstract/pipe.py#L88-L90). On a 3.12+ baseline this wants `asyncio.get_running_loop()` or explicit loop injection.
2. **There is still pre-`TaskGroup` / pre-structured-concurrency style code.**
   - `tasks` is the biggest example: [`tasks/tasks.py#L19-L447`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/tasks/tasks.py#L19-L447) manually coordinates queues, semaphores, and cancellation.
   - `pipe` still uses `asyncio.gather(asyncio.create_task(...))` in [`pipe/abstract/pipe.py#L182-L188`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/abstract/pipe.py#L182-L188).
3. **`asyncio.ensure_future()` survives in one place and should go.**
   - [`subprocess/async_subprocess.py#L55-L61`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/subprocess/async_subprocess.py#L55-L61) should be `create_task()` if the code remains at all.
4. **`pipe` is coupled to private asyncio internals.**
   - [`pipe/abstract/pipe.py#L139-L155`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/pipe/abstract/pipe.py#L139-L155) uses `asyncio.streams.FlowControlMixin` and direct `asyncio.StreamWriter(...)` construction. That is the shakiest code in the package on a forward-compat basis.
5. **`functional.__all__` contains a broken public export.**
   - [`functional/__init__.py#L23-L42`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/__init__.py#L23-L42) exports `buffered`, which is not imported or defined anywhere.
6. **`trycast` is only earning its keep in one place.**
   - It appears only in [`functional/utils.py#L12-L12`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/utils.py#L12-L12) for [`typed()`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/functional/utils.py#L85-L96). Given zero canonical consumers of `typed`, this dependency looks much easier to remove on a 3.12+ cleanup than I expected.
7. **`pytz` hangs around only in unexported date code.**
   - [`utils/date.py#L1-L10`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/date.py#L1-L10) uses `pytz.UTC`; on a 3.12+ baseline this should just be `datetime.timezone.utc` or `zoneinfo.ZoneInfo("UTC")` if that helper survives.
8. **There is at least one real bug, not just style drift.**
   - [`event/executive.py#L43-L51`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/event/executive.py#L43-L51) forwards `**kwargs` to `loop.run_in_executor()`, which does not accept keyword arguments for the target callable. That is a latent runtime `TypeError` if anyone ever uses kwargs there.
9. **There is one security-sensitive dated pattern.**
   - [`utils/data.py#L36-L39`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/utils/data.py#L36-L39) calls `tarfile.extractall()` without an explicit `filter=` on a Python 3.12 baseline.
10. **Typing style is mixed.**
   - A lot of code already uses `X | None`, which is good.
   - Some files still import ABC-ish types from `typing` rather than `collections.abc` / builtin generics, e.g. [`log/logging.py#L6-L8`](https://github.com/envoyproxy/toolshed/blob/4ef90607b906d06de3c9177bd0281e0651859fb8/py/aio.core/aio/core/log/logging.py#L6-L8).

---

## F. Recommended action plan

Grouped by verdict, sorted roughly by impact.

### KEEP-BUT-MODERNISE

1. **Modernise `functional.async_property` support code** — keep `async_property`, `Loader`, and `AwaitableGenerator`, but clean the surrounding plumbing (`Loader` internals, typing, docs). **Impact:** `async_property` has ~152 in-repo references across 11 packages, so this is the highest-value “keep” surface.
2. **Modernise `tasks.concurrent` / `Concurrent`** — retain the API, but revisit cancellation and task orchestration with 3.12 eyes (`TaskGroup` where appropriate, clearer lifecycle handling). **Impact:** 7 direct call sites across 5 packages, plus the exception types are part of downstream contracts.
3. **Modernise `event.AReactive` / `AExecutive`** — switch away from `get_event_loop()`, fix the `execute(..., **kwargs)` bug, and reconsider the default executor choice. **Impact:** 5+ packages directly depend on these mixins, and `directory` stacks on top of them.
4. **Modernise `pipe` without changing its shape** — keep the abstraction for `aio.api.bazel`, but remove private asyncio internals and use structured task management. **Impact:** all known consumers are in `aio.api.bazel`, so this is nicely scoped.

### DEPRECATE

1. **Deprecate `log.QueueLogger` in favor of stdlib logging handlers**. **Impact:** only 1 in-repo consumer (`aio.run.runner`), so migration is tiny.
2. **Deprecate `tasks.inflate`** and inline it at the 4 known call sites with plain `asyncio.gather()` / `TaskGroup` patterns. **Impact:** 2 packages, 4 refs.
3. **Deprecate `utils.captured_warnings` / `Captured`** in favor of `warnings.catch_warnings(record=True)`. **Impact:** 1 call site.
4. **Deprecate `utils.dottedname` / `dottedname_resolve`** in favor of `importlib.import_module()`. **Impact:** effectively 1 call site.
5. **Deprecate `utils.from_json`** — the one consumer can read + `json.loads()` inline. **Impact:** 1 call site.

### MOVE

1. **Move `directory` out of `aio.*`** — probably the strongest packaging mismatch in the package. Suggested destination: a generic fs/repo tooling package, not an async one. **Impact:** 17 references across `dependatool`, `envoy.base.utils`, and `envoy.code.check`.
2. **Move `subprocess` handler abstractions out of `aio.*`** — `ASubprocessHandler` / `ISubprocessHandler` are useful for `envoy.code.check`, but they are sync subprocess helpers, not asyncio helpers. **Impact:** 8 references in `envoy.code.check`, plus the exceptions module.
3. **Move `functional` query helpers (`CollectionQuery`, `QueryDict`, `qdict`, `functional.exceptions`) out of `aio.*`** — good utility, wrong home. **Impact:** small but real consumers in `aio.api.nist` and `envoy.dependency.check`.
4. **Move `dev.debug` out of `aio.*`** if it stays at all. **Impact:** 4 references in `envoy.code.check`.
5. **Move `utils.from_yaml`** if the YAML file convenience is still wanted; it has nothing to do with asyncio. **Impact:** 3 refs across 2 packages.

### DROP

1. **Drop the stale `functional.buffered` export immediately.** It is a broken public symbol today.
2. **Drop the unused `subprocess` async wrapper surface** — `AsyncSubprocess`, `run`, `parallel`. Canonical consumers: zero. Modern stdlib coverage: good enough.
3. **Drop public `directory` finder classes** — `ADirectoryFileFinder`, `AGitDirectoryFileFinder`, `DirectoryFileFinder`, `GitDirectoryFileFinder`. Keep them internal if needed; do not keep them public.
4. **Drop zero-consumer functional helpers** — `async_iterator`, `async_list`, `async_set`, `async_map`, `batches`, `batch_jobs`, `maybe_awaitable`, `maybe_coro`, `nested`, `typed`. The big easy win here is `batches` → `itertools.batched`.
5. **Drop zero-consumer utils** — `ellipsize`, `extract`, `ExtractError`, `is_sha`, `is_tarlike`, `to_yaml`.
6. **Drop `dev.timing`** — zero consumers, sync-only, generic.
7. **Drop public `QueueHandler`** if `QueueLogger` is deprecated; if the CancelledError behavior still matters, inline the tiny subclass near the one remaining logger setup rather than keeping it as top-level API.

---

## Bottom line

If I had to summarize the package in one sentence: **keep the genuinely asyncio-specific core (`async_property`, `AwaitableGenerator`, `concurrent`, `Loader`), modernise it for 3.12, and be much more ruthless about moving or dropping everything that is really “generic repo tooling with some async wrappers.”**

That is a much smaller cleanup than “rewrite `aio.core` around third-party libraries” — and it fits the repo’s current stdlib-first direction much better.
