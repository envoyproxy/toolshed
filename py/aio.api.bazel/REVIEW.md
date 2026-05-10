# `aio.api.bazel` — code review

_Generated 2026-05-10. Follow-up to the initial packaging cleanup pass (`name = aio_api_bazel` → `aio.api.bazel`, URL fix, dep-bound lowering, Py 3.12+ typing/syntax modernisation). Reviewed at commit [`5bd5e4f`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel)._

---

## Summary

`aio.api.bazel` is a small async wrapper around the Bazel CLI that also implements the Bazel persistent-worker protocol over stdin/stdout JSON framing. The code is clean and idiomatic for the toolshed `abstracts`-framework pattern, but several genuine correctness issues exist: the `cwd` parameter accepted by `ABazelRun.run` is silently dropped; startup options are never forwarded to `bazel run`; `ABazelWorkerProcessor._dump` always emits `exit_code=0`; the one-shot worker path is a silent no-op; and cancellation of async subprocess tasks is not propagated to the child process. Beyond those correctness gaps there are observable abstraction problems (the `ABazel` / `ABazelCommand` split earns nothing; the four concrete classes in `bazel.py` are empty boilerplate), testing weaknesses (heavy patching of `dict` / `json`, no edge-case coverage for empty output or non-zero return codes in the run path, no integration tests), and documentation gaps (copy-paste docstring, one-sentence README).

---

## Findings

### 1. Architectural / API-surface smells

#### 1.1 `ABazel` / `ABazelCommand` split earns nothing
- **Where**: [`aio/api/bazel/abstract/base.py:L15-L77`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/base.py#L15-L77)
- **What**: `ABazel` manages only `path` and `bazel_path`. `ABazelCommand` adds the executor / subprocess machinery. Every concrete or abstract subclass (`ABazelQuery`, `ABazelRun`, `ABazelEnv`) always extends `ABazelCommand`, never bare `ABazel`. The split implies a realistic use case where you have `path`/`bazel_path` but no subprocess capability, but no such class exists or is planned.
- **Why it matters**: Increases cognitive load when reading the hierarchy without providing an extension point that is ever used.
- **Suggested fix**: Merge `ABazelCommand` into `ABazel`; keep the same public methods. Remove the separate export of `ABazelCommand` from `__init__.py` or mark it as internal (`_ABazelCommand`).
- **Effort**: S
- **Risk**: low

#### 1.2 Four empty concrete classes in `bazel.py`
- **Where**: [`aio/api/bazel/bazel.py:L10-L41`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/bazel.py#L10-L41)
- **What**: `Bazel`, `BazelQuery`, `BazelRun`, and `BazelEnv` are the only "real" implementations. `BazelQuery` and `BazelRun` each have `pass` as their entire body. `Bazel.__init__` is inherited, and both `cached_property` overrides simply delegate to `super()`. This is mandatory boilerplate imposed by the `abstracts.implementer` decorator and adds no semantic value.
- **Why it matters**: Callers who want to understand what `BazelEnv` does must trace through the abstract chain. The `bazel.py` module adds a layer of files with no logic.
- **Suggested fix**: Evaluate whether the `abstracts.implementer` pattern genuinely helps here. If not, collapse the abstract + concrete pair into a single concrete class with regular `abc.ABC` enforcement.
- **Effort**: M
- **Risk**: medium (framework-level change)

#### 1.3 `IBazelWorker` / `IBazelProcessProtocol` interface layer duplicates `aio.core.pipe` contracts
- **Where**: [`aio/api/bazel/interface.py:L11-L54`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/interface.py#L11-L54)
- **What**: `IBazelProcessProtocol` extends `pipe.IProcessProtocol` with a `TODO` comment saying to move the same method to `aio.core.pipe.interface` and fix its type. `IBazelWorkerProcessor` similarly wraps `pipe.IStdinStdoutProcessor`. Two `# TODO: copy this to aio.core.pipe.interface and fix type` comments survive (L15 and L39/51).
- **Why it matters**: The interface boundary between `aio.core.pipe` and `aio.api.bazel` is unstable; downstream implementors cannot rely on it.
- **Suggested fix**: Either complete the move (add the method to `aio.core.pipe.interface`) or remove the TODO and document why the local interface must diverge.
- **Effort**: M
- **Risk**: low

#### 1.4 `ABazelWorker` is a full `runner.Runner` for a trivial stdin/stdout loop
- **Where**: [`aio/api/bazel/abstract/worker.py:L54-L92`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/worker.py#L54-L92)
- **What**: Inheriting from `runner.Runner` pulls in argparse setup, asyncio orchestration, and the full runner lifecycle for what is essentially a read→process→write loop. The extra surface area includes `extra_args`, `add_arguments`, and `persistent` — each needing its own test.
- **Why it matters**: Heavy base class makes it harder to embed the worker protocol in non-runner contexts (e.g., as a library component in tests or a different runner).
- **Suggested fix**: Factor out the worker-protocol loop into a standalone `BazelWorkerLoop` class that has no runner dependency, and keep the runner only for the CLI entry point.
- **Effort**: L
- **Risk**: medium

---

### 2. Bazel subprocess correctness

#### 2.1 `cwd` parameter in `ABazelRun.run` is silently dropped
- **Where**: [`aio/api/bazel/abstract/run.py:L16-L31`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/run.py#L16-L31)
- **What**: `run()` accepts `cwd: str = ""` but passes only `capture_output=capture_output` to `subproc_run`. The `cwd` argument is never forwarded, so callers who pass a non-empty `cwd` get silently ignored and the subprocess uses the default (`self.path`).
- **Why it matters**: Silent parameter-drop bugs are very hard to diagnose at a call site. Any caller that relies on this parameter gets incorrect behaviour without an error.
- **Suggested fix**:
  ```python
  resp = await self.subproc_run(
      bazel_args,
      capture_output=capture_output,
      **({"cwd": cwd} if cwd else {}))
  ```
- **Effort**: S
- **Risk**: low

#### 2.2 `ABazelRun.run` omits `bazel_startup_options`
- **Where**: [`aio/api/bazel/abstract/run.py:L25`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/run.py#L25)
- **What**: `bazel_args = (self.bazel_path, "run", target) + args`. Compare with `ABazelQuery.query_command` which correctly splices in `*self.bazel_startup_options`. Any startup options passed to the constructor (e.g., `--output_base`, `--bazelrc`) are applied to queries but ignored by `run`.
- **Why it matters**: Inconsistent behaviour between query and run; startup options that affect the workspace (e.g., `--output_base`) are ignored silently.
- **Suggested fix**:
  ```python
  bazel_args = (
      (str(self.bazel_path),)
      + tuple(self.bazel_startup_options)
      + ("run", target)
      + args)
  ```
- **Effort**: S
- **Risk**: low

#### 2.3 `executor` property allocates a new `ThreadPoolExecutor` on every access
- **Where**: [`aio/api/bazel/abstract/base.py:L46-L47`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/base.py#L46-L47)
- **What**: `executor` is a plain `@property` that returns `concurrent.futures.ThreadPoolExecutor()` fresh each time. `subproc_run` uses it as a context manager, so each subprocess call spins up and tears down a thread pool. Creating a `ThreadPoolExecutor` involves OS-level thread allocation.
- **Why it matters**: For workloads that run many bazel queries (e.g., dependency checks), this creates unnecessary thread-pool churn. The public property also leaks executor handles to callers who access it directly.
- **Suggested fix**: Use a `@cached_property` (or pass the executor as a constructor argument). If per-call isolation is required, use `concurrent.futures.thread.ThreadPoolExecutor(max_workers=1)` and document the design choice.
- **Effort**: S
- **Risk**: low

#### 2.4 Async cancellation not propagated to subprocess
- **Where**: [`aio/api/bazel/abstract/base.py:L53-L67`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/base.py#L53-L67)
- **What**: `subproc_run` runs `subprocess.run` in a thread-pool executor via `loop.run_in_executor`. If the asyncio task is cancelled while the subprocess is running, `asyncio.CancelledError` is raised in the coroutine but the executor thread continues blocking until the subprocess finishes. The subprocess becomes an orphan.
- **Why it matters**: In a CI environment with timeouts, cancelled tasks leave behind dangling `bazel` processes that consume CPU/memory and hold workspace locks. On subsequent runs, Bazel may fail because it cannot acquire the workspace lock.
- **Suggested fix**: Switch to `asyncio.create_subprocess_exec` for the subprocess call, which is natively async and propagates cancellation correctly. Alternatively, use a `Process` object returned by `subprocess.Popen` inside the executor thread and `process.kill()` on cancellation.
- **Effort**: M
- **Risk**: medium

#### 2.5 `ABazelQuery.query_failed` uses a fragile stdout-content heuristic
- **Where**: [`aio/api/bazel/abstract/query.py:L56-L60`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/query.py#L56-L60)
- **What**: `response.stdout.strip().startswith("[bazel release")` is checked as a secondary failure condition (after `returncode`). This exists to catch the case where Bazel prints a release banner to stdout and the returncode is 0. However, this string can legitimately appear as the first line of a label (e.g., a target literally named `[bazel release`), and it will false-positive on any future Bazel version that changes the release-notes format.
- **Why it matters**: Silent false failures on legitimate query results; breakage when Bazel changes its output format.
- **Suggested fix**: Remove this heuristic and rely solely on `returncode`. If Bazel's stdout-contamination behaviour is a real concern for the versions being targeted, document it with a comment and a link to the Bazel issue.
- **Effort**: S
- **Risk**: low

#### 2.6 `query_kwargs` redundantly overrides `cwd` already set by `_subproc_run`
- **Where**: [`aio/api/bazel/abstract/query.py:L16-L21`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/query.py#L16-L21)
- **What**: `query_kwargs` returns `dict(cwd=str(self.path), encoding="utf-8")`. `_subproc_run` already defaults `cwd` to `self.path` when not supplied. The explicit `cwd=str(self.path)` in `query_kwargs` is therefore redundant — but it also converts `Path` to `str` (necessary for older subprocess versions). Providing `cwd` twice (once via `query_kwargs`, once as the default in `_subproc_run`) obscures which value wins.
- **Why it matters**: Minor confusion; if `_subproc_run`'s default-cwd logic ever changes, `query_kwargs` creates a silent conflict.
- **Suggested fix**: Remove the `cwd` from `query_kwargs` and instead ensure `_subproc_run` converts `Path → str` before passing to `subprocess.run`.
- **Effort**: S
- **Risk**: low

---

### 3. Bazel worker lifecycle

#### 3.1 Non-persistent worker path is a silent no-op
- **Where**: [`aio/api/bazel/abstract/worker.py:L88-L92`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/worker.py#L88-L92)
- **What**: When `self.persistent` is `False`, `ABazelWorker.run()` does nothing and returns `None`. The entry-point `worker_cmd` will then call `sys.exit(main())` → `sys.exit(None)` → exit code 0. A caller running the worker without `--persistent_worker` gets a silent success.
- **Why it matters**: The `# TODO: implement one-shot op` comment confirms this is not intentional behaviour. Bazel's worker protocol specifies a one-shot mode; not implementing it makes the binary useless as a non-persistent worker.
- **Suggested fix**: Either raise `NotImplementedError` immediately (to make the gap explicit), or implement the one-shot path that reads one request from stdin, processes it, and exits.
- **Effort**: M
- **Risk**: medium

#### 3.2 `_dump` always emits `exit_code=0` regardless of processing outcome
- **Where**: [`aio/api/bazel/abstract/worker.py:L45-L47`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/worker.py#L45-L47)
- **What**: `_dump` unconditionally produces `{"exit_code": 0, "output": msg}`. The `# TODO: add error handling` comment acknowledges the gap. Bazel's persistent-worker protocol treats `exit_code != 0` as a worker failure and re-queues the work item; always returning 0 means Bazel will silently treat every response as a success even when the protocol handler threw an exception.
- **Why it matters**: Correctness bug in the worker protocol. Failed work items are reported as succeeded to Bazel, leading to incorrect build results or silent caching of failures.
- **Suggested fix**: Pass `exit_code` as a parameter to `_dump`; set it to 1 (and populate `output` with the error message) when `process()` raises. Update `process()` and `send()` accordingly.
- **Effort**: M
- **Risk**: medium

#### 3.3 Worker processor has no EOF / shutdown handling
- **Where**: [`aio/api/bazel/abstract/worker.py:L29-L51`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/worker.py#L29-L51)
- **What**: `ABazelWorkerProcessor` inherits from `pipe.StdinStdoutProcessor`. There is no evidence (in this package) that EOF on stdin causes a clean exit, or that `asyncio.CancelledError` / `KeyboardInterrupt` during the `recv→process→send` loop is caught and leads to a graceful shutdown.
- **Why it matters**: Bazel sends SIGTERM to workers it wants to shut down. Without a SIGTERM handler and clean loop exit, the worker may hang or leave Bazel waiting indefinitely for a response.
- **Suggested fix**: Audit `pipe.StdinStdoutProcessor.__call__` in `aio.core` to confirm it handles EOF and cancellation; if not, add `try/except asyncio.CancelledError` around the loop and flush/close stdout before exiting.
- **Effort**: M
- **Risk**: medium

---

### 4. Async correctness

#### 4.1 `ABazelCommand.loop` is a computed `@property`; loop reference should be stable
- **Where**: [`aio/api/bazel/abstract/base.py:L49-L51`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/base.py#L49-L51)
- **What**: `loop` calls `asyncio.get_running_loop()` on every access. Because this is only called from within `_run_in_executor` (which is already `async`), there is always a running loop and the call is safe. However, it is a public property, and callers who access `.loop` outside an async context will receive a `RuntimeError`.
- **Why it matters**: Surprising API; public properties should not raise `RuntimeError` in non-async contexts unless documented. The property name implies a stable attribute.
- **Suggested fix**: Either make it a private helper `_get_loop()`, or annotate / document that it must only be called from an async context.
- **Effort**: S
- **Risk**: low

#### 4.2 Blocking `subprocess.run` called from a thread, not natively async
- **Where**: [`aio/api/bazel/abstract/base.py:L69-L76`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/base.py#L69-L76)
- **What**: `_subproc_run` calls `subprocess.run(...)` (a blocking call) inside an executor thread. Using `asyncio.create_subprocess_exec` + `asyncio.wait_for` would keep everything on the event loop, avoid thread overhead, support native cancellation, and stream output without capturing it all in memory.
- **Why it matters**: Thread-pool approach limits parallelism (thread count ≤ pool size), prevents natural cancellation propagation (finding 2.4), and adds latency for short-lived processes due to thread-pool startup.
- **Suggested fix**: Replace the executor / `subprocess.run` pattern with `asyncio.create_subprocess_exec`. The public API of `subproc_run` stays the same; internal implementation switches to native async subprocess.
- **Effort**: M
- **Risk**: medium

---

### 5. Query / output parsing

#### 5.1 Empty query output produces `[""]` instead of `[]`
- **Where**: [`aio/api/bazel/abstract/query.py:L42`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/query.py#L42)
- **What**: `response.stdout.strip().split("\n")` — when Bazel returns an empty result set (valid for a query with no matching targets), `stdout` is `""` or `"\n"`. After `strip()`, `"".split("\n")` returns `[""]` (a list with one empty string), not `[]`.
- **Why it matters**: Callers iterating over query results will process one spurious empty-string entry, potentially causing `AttributeError` or incorrect logic downstream.
- **Suggested fix**:
  ```python
  lines = response.stdout.strip().split("\n")
  return [l for l in lines if l]
  ```
- **Effort**: S
- **Risk**: low

#### 5.2 Error message has no separator between stdout and stderr
- **Where**: [`aio/api/bazel/abstract/query.py:L40-L41`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/query.py#L40-L41)
- **What**: `f"\n{response.stdout.strip()}{response.stderr.strip()}"` — stdout and stderr are concatenated without any delimiter. If both are non-empty, the resulting error string is ambiguous.
- **Why it matters**: Makes debugging query failures harder; users cannot tell where stdout ends and stderr begins.
- **Suggested fix**: `f"\nstdout:\n{response.stdout.strip()}\nstderr:\n{response.stderr.strip()}"`.
- **Effort**: S
- **Risk**: low

#### 5.3 No support for `cquery` / `aquery` variants
- **Where**: [`aio/api/bazel/abstract/query.py`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/query.py)
- **What**: Only `bazel query` is supported. `bazel cquery` (configurable query for transitions/selects) and `bazel aquery` (action graph query) are distinct Bazel commands with different output formats that many real-world use cases require.
- **Why it matters**: Downstream consumers wanting to resolve build configurations or inspect actions must implement their own subprocess calls, defeating the purpose of this library.
- **Suggested fix**: Add an optional `command: str = "query"` parameter to `query_command` to support `cquery`/`aquery`; callers pass `command="cquery"`.
- **Effort**: S
- **Risk**: low

---

### 6. Caching / memoisation

#### 6.1 `ABazelQuery.query_kwargs` is `@property` but produces a new dict each call
- **Where**: [`aio/api/bazel/abstract/query.py:L16-L21`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/query.py#L16-L21)
- **What**: `run_query` calls `self.query_kwargs.copy()` — already `.copy()` implies the original is shared, but since `query_kwargs` is a `@property` that creates a new dict each time, the `.copy()` call is redundant.
- **Why it matters**: Minor inefficiency and misleading API (the `.copy()` call in `run_query` implies the dict is a shared mutable object, but it is not).
- **Suggested fix**: Change to `@cached_property` (since `path` is stable); remove the `.copy()` call in `run_query`.
- **Effort**: S
- **Risk**: low

#### 6.2 `ABazelEnv.bazel_query` and `bazel_run` resolve `bazel_path` eagerly at first query
- **Where**: [`aio/api/bazel/abstract/env.py:L15-L31`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/env.py#L15-L31)
- **What**: `bazel_query = self.bazel_query_class(self.path, bazel_path=self.bazel_path)` — accessing `self.bazel_path` triggers `shutil.which("bazel")` if no explicit path was given. This path is then frozen into the `BazelQuery` / `BazelRun` instances. If the environment changes between construction and the first query (unusual but possible in tests with `PATH` mocking), the cached resolution is stale.
- **Why it matters**: Subtle ordering dependency; `bazel_path` being resolved at instantiation of the sub-object means any test that patches `shutil.which` after constructing `BazelEnv` may observe incorrect behavior.
- **Suggested fix**: Pass a callable/lambda for `bazel_path` rather than the resolved value, or accept that this is intentional and document it.
- **Effort**: S
- **Risk**: low

---

### 7. Error handling

#### 7.1 `ABazelWorkerProcessor._load` has no error handling for malformed JSON
- **Where**: [`aio/api/bazel/abstract/worker.py:L49-L51`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/worker.py#L49-L51)
- **What**: `json.loads(recv)["arguments"]` — if `recv` is not valid JSON, `json.JSONDecodeError` propagates unhandled up through the `recv → process → send` loop. If `"arguments"` is missing from the JSON object, `KeyError` propagates similarly.
- **Why it matters**: A single malformed message from Bazel crashes the worker process. Bazel will then restart the worker, potentially losing build state.
- **Suggested fix**: Wrap in `try/except (json.JSONDecodeError, KeyError) as e:` and call `self.send` with an error exit code (once finding 3.2 is fixed) before re-raising or returning a sentinel.
- **Effort**: S
- **Risk**: low

#### 7.2 `ABazelRun` error message uses raw `repr(CompletedProcess)`
- **Where**: [`aio/api/bazel/abstract/run.py:L30`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/run.py#L30)
- **What**: `raise exceptions.BazelRunError(f"Bazel run failed: {resp}")` — `str(CompletedProcess)` includes the full stdout and stderr byte strings in the message. For a `bazel run` command that produces megabytes of output (e.g., a failed binary startup), the exception message is enormous.
- **Why it matters**: Exceptions with multi-megabyte messages are difficult to log, display, or store; they also expose potentially sensitive build output in tracebacks.
- **Suggested fix**: Include only `returncode` and a truncated stderr:
  ```python
  raise exceptions.BazelRunError(
      f"Bazel run failed (exit {resp.returncode}):"
      f"\n{(resp.stderr or b'').decode(errors='replace')[:2000]}")
  ```
- **Effort**: S
- **Risk**: low

#### 7.3 `raises=False` in `ABazelRun.run` silently returns failure
- **Where**: [`aio/api/bazel/abstract/run.py:L20-L31`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/run.py#L20-L31)
- **What**: When `raises=False` and `returncode != 0`, the caller gets a `CompletedProcess` with a non-zero exit code. There is no logging, no warning, and no documented expectation that the caller will check `returncode`.
- **Why it matters**: Easy to write `await env.run("//foo", raises=False)` and never check the result, silently ignoring a build failure.
- **Suggested fix**: Log a warning when `raises=False` and returncode is non-zero. Alternatively, remove `raises` as a parameter and always raise; let callers `catch BazelRunError` when they need to handle failure.
- **Effort**: S
- **Risk**: low

---

### 8. Logging / observability

#### 8.1 Zero logging in the entire package
- **Where**: All files in [`aio/api/bazel/`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/)
- **What**: No `import logging` anywhere. Subprocess invocations, query expressions, return codes, captured stderr, and worker protocol messages are never logged.
- **Why it matters**: Debugging CI failures requires re-running with extra `print` calls or monkeypatching. Ops visibility into what Bazel commands were run and what they returned is zero.
- **Suggested fix**: Add a module-level `log = logging.getLogger(__name__)` in each module; log at `DEBUG` level before each subprocess call (command + cwd), and at `WARNING` level when stderr is non-empty on a successful query.
- **Effort**: S
- **Risk**: low

#### 8.2 Captured Bazel stderr is discarded on success
- **Where**: [`aio/api/bazel/abstract/query.py:L35-L42`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/query.py#L35-L42)
- **What**: `handle_query_response` returns `response.stdout.strip().split("\n")` on success, discarding `response.stderr`. Bazel often prints deprecation warnings, fetch progress, and `INFO` messages to stderr even for successful queries.
- **Why it matters**: Warnings from Bazel (e.g., "this attribute is deprecated") are silently swallowed, making it impossible to detect impending breakage.
- **Suggested fix**: Log `response.stderr` at `DEBUG` (always) or `WARNING` (if non-empty) before returning the result.
- **Effort**: S
- **Risk**: low

---

### 9. Type-annotation correctness

#### 9.1 `ABazelEnv.query` return type is `list` instead of `list[str]`
- **Where**: [`aio/api/bazel/abstract/env.py:L33`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/env.py#L33)
- **What**: `async def query(self, query: str, **kwargs) -> list:` — the unparameterised `list` loses the element type. The actual return type is `list[str]` (from `ABazelQuery.__call__`).
- **Why it matters**: Mypy treats `list` as `list[Any]`, neutralising all downstream type checking on the result.
- **Suggested fix**: Change to `-> list[str]`.
- **Effort**: S (trivial)
- **Risk**: low

#### 9.2 `ABazelCommand.subproc_run` / `_subproc_run` use untyped `*args, **kwargs`
- **Where**: [`aio/api/bazel/abstract/base.py:L53-L76`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/base.py#L53-L76)
- **What**: All three subprocess-related methods use `*args, **kwargs` without type annotations. Callers have no idea what arguments are accepted without reading the implementation.
- **Why it matters**: Defeats static checking at call sites; makes the public API opaque.
- **Suggested fix**: Use explicit typed signatures: `cmd: Sequence[str | os.PathLike]`, forwarding known kwargs (`cwd`, `encoding`, `capture_output`, `timeout`).
- **Effort**: S
- **Risk**: low

#### 9.3 `# type:ignore` in `interface.py` without justification
- **Where**: [`aio/api/bazel/interface.py:L24`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/interface.py#L24), [`L29`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/interface.py#L29)
- **What**: `# type:ignore` (without an error code) is used on `@property` / `@abstracts.interfacemethod` stacking in `IBazelWorker`. The ignore suppresses an error the `abstracts` framework generates when combining property decorators, but the reason is undocumented.
- **Why it matters**: Silent suppression of type errors can mask genuine mistakes; future mypy upgrades may change what is being ignored.
- **Suggested fix**: Replace with `# type: ignore[misc]` (or the appropriate error code) and add an inline comment explaining the interaction with `abstracts`.
- **Effort**: S (trivial)
- **Risk**: low

#### 9.4 `IBazelWorkerProcessor.__call__` accepts `*args` and returns `Any`
- **Where**: [`aio/api/bazel/interface.py:L53`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/interface.py#L53)
- **What**: `def __call__(self, *args) -> Any:` — the interface method for the callable protocol is completely untyped. The actual implementation in `pipe.StdinStdoutProcessor` (in `aio.core`) presumably takes no arguments and is `async`.
- **Why it matters**: Callers cannot know the calling convention from the interface.
- **Suggested fix**: Type as `async def __call__(self) -> None:` if that matches the implementation, or as a `Callable[[], Awaitable[None]]` protocol.
- **Effort**: S
- **Risk**: low

#### 9.5 `ABazelWorker.protocol_class` `@cached_property` shadows `IBazelWorker` interface type
- **Where**: [`aio/api/bazel/abstract/worker.py:L73-L75`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/worker.py#L73-L75)
- **What**: `ABazelWorker.protocol_class` is a `@cached_property` returning `type[pipe.IProcessProtocol]`, whereas `IBazelWorker.protocol_class` is typed as `type[IBazelProcessProtocol]`. `IBazelProcessProtocol` is a subtype of `IProcessProtocol`, so `ABazelWorker.protocol_class` returns a broader type than the interface promises.
- **Why it matters**: Callers using the interface type will get a wider type than documented; the `abstracts` framework may not catch this mismatch.
- **Suggested fix**: Narrow the return type of `ABazelWorker.protocol_class` to `type[interface.IBazelProcessProtocol]`.
- **Effort**: S
- **Risk**: low

---

### 10. Testing smells

#### 10.1 `BazelQuery` and `BazelRun` tests only assert `__init__` was called
- **Where**: [`tests/test_bazel.py:L62-L96`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/tests/test_bazel.py#L62-L96)
- **What**: `test_bazel_bazel_query` and `test_bazel_bazel_run` instantiate the classes, verify `ABazelQuery.__init__` / `ABazelRun.__init__` was called with the right args, and do nothing else. Since the class bodies are `pass`, this is as much as there is to test — but the tests give false confidence.
- **Why it matters**: If new behaviour is added to these concrete classes, there is no existing test structure to extend.
- **Suggested fix**: These tests are fine as-is given the `pass` bodies, but add a comment explaining why they are minimal, and add a smoke-test that exercises the full query path end-to-end using a mock subprocess.
- **Effort**: S
- **Risk**: low

#### 10.2 `cwd` parameter in `ABazelRun.run` is not tested for forwarding
- **Where**: [`tests/test_abstract_run.py:L72-L116`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/tests/test_abstract_run.py#L72-L116)
- **What**: The `cwd` parameter is accepted by `run()` and is parametrised in the test, but the assertion only checks `m_run.call_args == [((m_bazel.return_value, "run", "TARGET") + args,), dict(capture_output=...)]` — `cwd` is never asserted. This is consistent with the actual bug (finding 2.1) where `cwd` is dropped.
- **Why it matters**: The test is a 1:1 mirror of the (broken) implementation. Adding a `cwd` assertion would have caught the bug.
- **Suggested fix**: Add assertion `dict(capture_output=..., cwd=cwd_value_when_set)` to the `m_run.call_args` check.
- **Effort**: S
- **Risk**: low

#### 10.3 `test_bazelworkerprocessor__dump` patches `dict` and `json` individually
- **Where**: [`tests/test_abstract_worker.py:L143-L162`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/tests/test_abstract_worker.py#L143-L162)
- **What**: The test patches both `dict` and `json` as global names in the module. Patching `dict` is highly unusual and makes the test extremely brittle — any refactoring that changes how the dict literal is written (e.g., using `|` merge syntax) will silently break the mock setup.
- **Why it matters**: Fragile test. Equally, patching `json.dumps` alone is sufficient and much less brittle.
- **Suggested fix**: Remove the `dict` patch; assert the actual JSON output string (or parse it) to verify correctness without over-mocking.
- **Effort**: S
- **Risk**: low

#### 10.4 No test for empty query output (`[""]` vs `[]`)
- **Where**: [`tests/test_abstract_query.py`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/tests/test_abstract_query.py)
- **What**: `test_base_bazel_query_handle_query_response` tests the `failed=True/False` paths but does not test empty stdout (the `[""]` bug in finding 5.1).
- **Why it matters**: The bug would have been caught by a simple parametrised case `("", [])`.
- **Suggested fix**: Add `@pytest.mark.parametrize("stdout,expected", [("", []), ("//a\n//b", ["//a", "//b"])])`.
- **Effort**: S
- **Risk**: low

#### 10.5 No tests for `ABazelRun` startup-options omission
- **Where**: [`tests/test_abstract_run.py`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/tests/test_abstract_run.py)
- **What**: `test_base_bazel_run_run` does not assert that `self.bazel_startup_options` is included in `bazel_args`. This mirrors the bug in finding 2.2.
- **Why it matters**: Test mirrors broken implementation.
- **Suggested fix**: Add a `startup_options` parametrised case to `test_base_bazel_run_run` and assert the options appear in the command tuple.
- **Effort**: S
- **Risk**: low

#### 10.6 No integration or smoke tests
- **Where**: [`tests/`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/tests/)
- **What**: All tests are pure unit tests using heavy mocking. There is no test that actually invokes any Bazel command (even `bazel version`), no test that reads/writes to real stdin/stdout, and no test for the worker protocol message loop end-to-end.
- **Why it matters**: The mocked unit tests give no assurance that the library works with an actual Bazel binary or in a real asyncio event loop.
- **Suggested fix**: Add an optional integration test (guarded by `pytest.importorskip` or a `--integration` flag) that runs `bazel version` via `BazelEnv` against a real workspace.
- **Effort**: M
- **Risk**: low

#### Minor nits
- **10.N1** `test_base_bazel_query_query` checks `m_query.call_args == [("EXPRESSION",), kwargs]` but does not verify `query_options` is forwarded correctly when given. The forwarding is tested in `test_base_bazel_query_run_query`, so it is indirectly covered, but `test_base_bazel_query_query` could be cleaner.
- **10.N2** Several test functions use `[f"K{i}": f"V{i}" for i in range(0, 5)]` pattern for kwargs — `range(0, 5)` is identical to `range(5)` and the former is noise.

---

### 11. Dead / duplicated / commented-out code

#### 11.1 `worker_cmd.py` contains dead `if __name__ == "__main__":` block
- **Where**: [`aio/api/bazel/worker_cmd.py:L14-L16`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/worker_cmd.py#L14-L16)
- **What**: The `aio.bazel.worker` console-script entry point is registered in `setup.cfg:L55`, pointing to `aio.api.bazel:worker_cmd`. The `if __name__ == "__main__": worker_cmd()` block in `worker_cmd.py` is therefore unreachable in normal deployment (the module is imported, not run directly).
- **Why it matters**: Dead code creates confusion about the intended invocation path.
- **Suggested fix**: Remove the `if __name__ == "__main__"` block; move it to the top-level package `__init__.py` if direct invocation is ever needed.
- **Effort**: S (trivial)
- **Risk**: low

#### 11.2 `main()` wrapper in `worker_cmd.py` adds no value
- **Where**: [`aio/api/bazel/worker_cmd.py:L7-L8`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/worker_cmd.py#L7-L8)
- **What**: `def main(*args): return BazelWorker(*args)()` — this one-liner is only called from `worker_cmd` (and the dead `__main__` block). Inlining it would simplify the module.
- **Why it matters**: Very minor; thin wrapper adds a stack frame and an extra symbol in the module's namespace.
- **Suggested fix**: Inline into `worker_cmd`: `sys.exit(BazelWorker(*sys.argv[1:])())`.
- **Effort**: S (trivial)
- **Risk**: low

#### 11.3 Three TODO comments for unfinished protocol design
- **Where**: [`aio/api/bazel/interface.py:L15`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/interface.py#L15), [`L39`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/interface.py#L39), [`aio/api/bazel/abstract/worker.py:L46`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/worker.py#L46), [`L92`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/worker.py#L92)
- **What**: Four TODO comments document design decisions that were never implemented:
  - L15, L39: "copy this to aio.core.pipe.interface and fix type"
  - worker.py L46: "add error handling" in `_dump`
  - worker.py L92: "implement one-shot op"
- **Why it matters**: TODOs that survive into stable library code indicate deferred correctness work. Two of these (exit-code and one-shot) are functional gaps (findings 3.1 and 3.2).
- **Suggested fix**: Convert to GitHub issues and remove from source, or fix them (findings 3.1, 3.2).
- **Effort**: S
- **Risk**: low

#### 11.4 `ABazelCommand` exported publicly but only used internally
- **Where**: [`aio/api/bazel/__init__.py:L4`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/__init__.py#L4), [`__all__` L31-L56](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/__init__.py#L31-L56)
- **What**: `ABazelCommand` is re-exported from the top-level `__init__.py` and is part of `__all__`, but it is never referenced outside the `aio.api.bazel` package. Its only purpose is as an intermediate base class for `ABazelQuery`, `ABazelRun`, and `ABazelEnv`.
- **Why it matters**: Widening the public API surface unnecessarily; any change to `ABazelCommand` becomes a breaking API change.
- **Suggested fix**: Remove from `__all__` and the top-level import; mark it `_ABazelCommand` if it must remain as an extension point.
- **Effort**: S
- **Risk**: low (semver-major only if consumers are using it)

---

### 12. Documentation

#### 12.1 `ABazelEnv.run` docstring says "Run a bazel query"
- **Where**: [`aio/api/bazel/abstract/env.py:L37`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/env.py#L37)
- **What**: `"""Run a bazel query and return stdout as list of lines."""` — this is a copy-paste from `ABazelEnv.query`. The `run` method invokes `bazel run`, not `bazel query`, and does not return stdout as a list of lines (it returns `subprocess.CompletedProcess`).
- **Why it matters**: Incorrect docstring directly misleads callers about the method's return type and behaviour.
- **Suggested fix**: `"""Run a bazel target and return the subprocess result."""`
- **Effort**: S (trivial)
- **Risk**: low

#### 12.2 `README.rst` is a single-sentence stub
- **Where**: [`README.rst`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/README.rst)
- **What**: The entire README is "Async wrapper around bazel" (6 words). There are no usage examples, no explanation of the Bazel worker protocol, no description of the class hierarchy, and no mention of the `aio.bazel.worker` entry point.
- **Why it matters**: Makes it difficult for new contributors or consumers to understand how to use the package without reading all source files.
- **Suggested fix**: Add a quick-start section showing how to construct `BazelEnv`, run a query, and run a target. Add a separate section explaining the worker protocol and the `--persistent_worker` flag.
- **Effort**: S
- **Risk**: low

#### 12.3 Public abstract methods lack docstrings
- **Where**: [`aio/api/bazel/abstract/base.py:L26-L40`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/base.py#L26-L40), [`abstract/env.py:L19-L31`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/aio.api.bazel/aio/api/bazel/abstract/env.py#L19-L31)
- **What**: `ABazel.bazel_path` and `ABazel.path` have docstrings; `ABazelEnv.bazel_query_class` and `bazel_run_class` do not. The interface methods in `IBazelWorker` / `IBazelWorkerProcessor` also lack docstrings.
- **Why it matters**: Missing docstrings on interface methods make it harder to implement them correctly.
- **Suggested fix**: Add one-line docstrings to all `@abstractmethod` / `@abstracts.interfacemethod` properties.
- **Effort**: S (trivial)
- **Risk**: low

---

## Recommended follow-up PRs

| # | Title | Finding IDs | Effort | Risk |
|---|-------|------------|--------|------|
| 1 | **Fix `cwd` and startup-options omission in `ABazelRun.run`** | 2.1, 2.2 | S | low |
| 2 | **Fix empty-query output and error-message format in `ABazelQuery`** | 5.1, 5.2, 8.2 | S | low |
| 3 | **Fix worker protocol: `exit_code`, one-shot mode, and JSON error handling** | 3.1, 3.2, 7.1 | M | medium |
| 4 | **Switch subprocess to `asyncio.create_subprocess_exec` (cancellation safety)** | 2.4, 4.2 | M | medium |
| 5 | **Add logging throughout the package** | 8.1, 8.2 | S | low |
| 6 | **Tighten type annotations** (`list[str]`, `*args`/`**kwargs`, `# type:ignore` codes, `__call__` signature) | 9.1, 9.2, 9.3, 9.4, 9.5 | S | low |
| 7 | **Collapse `ABazel` / `ABazelCommand`; de-export `ABazelCommand` from public API** | 1.1, 11.4 | S | low |
| 8 | **Fix and expand test coverage** (cwd forwarding, startup options, empty output, `_dump` without patching `dict`) | 10.1–10.5, 10.N1 | S | low |
| 9 | **Documentation pass** (README usage examples, docstring corrections, TODO → GitHub issues) | 11.3, 12.1, 12.2, 12.3 | S | low |
| 10 | **Add `cquery`/`aquery` support and remove `[bazel release` heuristic** | 2.5, 5.3 | S | low |
