# `envoy.docs.sphinx_runner` — code review

_Generated 2026-05-10. Follow-up to the initial packaging cleanup pass._

## Summary

`envoy.docs.sphinx_runner` is a moderately complex (~370 LOC in `runner.py`) Sphinx
orchestration harness that wraps `sphinx.cmd.build.main` behind an `aio.run.Runner`
lifecycle. The code is readable and the happy path is well covered by unit tests, but
several structural problems accumulate risk: the `run()` coroutine calls only blocking
sync code (making the `async` wrapper hollow), a `FileNotFoundError` escapes
`check_env()` when a version-history file is absent, the `debug()` timing helper is
stale dead code, the vendored `sphinx_tabs` copy is untested and carries a single-file
module-level startup cost, and the `py_compatible` Python-version guard is off-by-four
versions. Documentation and type-annotation coverage are thin throughout the extension
files. Fixing the async and error-handling issues is medium effort and medium risk;
everything else is low effort and low risk. Total remediation could reasonably be split
into ~6 self-contained PRs.

---

## Findings

### 1. Architectural / API-surface smells

#### 1.1 `SphinxRunner` carries too many distinct responsibilities

- **Where**: [`runner.py` L54–L363](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L54-L363)
- **What**: A single class handles argument parsing, version computation, Docker-image-tag logic, `intersphinx_mapping` derivation, config-file writing, RST tarball extraction, Sphinx invocation, HTML archiving, and environment validation. There is no meaningful separation of concerns.
- **Why it matters**: Any change to any one concern risks breaking the others; the class is hard to unit-test in isolation (the test file mirrors this, patching nearly every property for each test).
- **Suggested fix**: Extract at least two natural seams — a `VersionInfo` data class (covering `version_number`, `version_string`, `docs_tag`, `blob_sha`, `docker_image_tag_name`, `release_level`) and a `BuildConfig` factory — so `SphinxRunner` can delegate to them. Compare the pattern in `envoy.dependency.check` where concerns are split across multiple mixins/classes.
- **Effort**: L
- **Risk**: medium

#### 1.2 `_build_dir` class variable is dead code

- **Where**: [`runner.py` L55](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L55)
- **What**: `_build_dir = "."` is declared on the class but the `build_dir` property always returns `pathlib.Path(self.tempdir.name)` — `_build_dir` is never read anywhere in the codebase.
- **Why it matters**: Dead attributes confuse readers who assume the class variable is intentionally overridable.
- **Suggested fix**: Delete the class variable. If the intent was to allow injection of a non-temp build directory, add an explicit `--build_dir` argument instead.
- **Effort**: S
- **Risk**: low

#### 1.3 `validate_args` raises the wrong exception type

- **Where**: [`runner.py` L355–L360](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L355-L360)
- **What**: `validate_args()` raises `SphinxBuildError` when `--overwrite` is absent and the output already exists. The error has nothing to do with a Sphinx build — it is an argument validation failure.
- **Why it matters**: `run()` catches `SphinxBuildError` and prints it, silently swallowing the exit code; callers who grep logs for `SphinxBuildError` will be misled about the source of failure.
- **Suggested fix**: Introduce a `SphinxArgError` (or reuse `SphinxEnvError`) for pre-flight failures, or call `parser.error()` to surface proper argument errors with usage text.
- **Effort**: S
- **Risk**: low

#### 1.4 `intersphinx_mapping` is always populated in `configs` but typed as optional

- **Where**: [`runner.py` L115](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L115), [`runner.py` L47–L51](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L47-L51)
- **What**: `ConfigDict` inherits from `BaseConfigDict` with `total=False`, making `intersphinx_mapping` optional; but the code always assigns it (`_configs["intersphinx_mapping"] = self.intersphinx_mapping`), so it is never actually absent.
- **Why it matters**: The TypedDict gives incorrect typing information; downstream code may not guard against a missing `intersphinx_mapping` key.
- **Suggested fix**: Move `intersphinx_mapping` into `BaseConfigDict` (mandatory). Leave only genuinely optional keys (`validator_path`, `descriptor_path`, `skip_validation`) in the `total=False` subclass.
- **Effort**: S
- **Risk**: low

#### 1.5 `cmd.py` `main()` silently discards its return value in some callers

- **Where**: [`cmd.py` L7–L12](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/cmd.py#L7-L12)
- **What**: `main()` returns `SphinxRunner(*args)()` (an `int | None`), and `cmd()` passes it straight to `sys.exit()`, which is correct. However `main` is also exported in `__all__` as a public API, and callers who import and call `main()` without checking the return value will miss exit-code propagation.
- **Why it matters**: Library misuse is silent; build-system integrations that call `main()` programmatically may not detect failures.
- **Suggested fix**: Add a return-type annotation `-> int` (enforcing `run()` to always return an `int`) and document the convention in the docstring.
- **Effort**: S
- **Risk**: low

---

### 2. Sphinx integration

#### 2.1 `html_dir` is hard-coded to `generated/html` regardless of `--build_target`

- **Where**: [`runner.py` L148–L150](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L148-L150), [`runner.py` L205–L217](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L205-L217)
- **What**: `sphinx_args` passes `str(self.html_dir)` as the Sphinx output directory, but `html_dir` is always `<build_dir>/generated/html` even when `build_target` is `dirhtml`, `singlehtml`, or `epub`. The directory name is misleading and `save_html()` will blindly tar whatever ends up there.
- **Why it matters**: Non-HTML build targets produce output in the "wrong" place; the misnaming is a maintenance trap for anyone adding a new target.
- **Suggested fix**: Rename `html_dir` → `output_dir` and derive it from `build_target` (e.g. `self.build_dir / "generated" / self.build_target`).
- **Effort**: S
- **Risk**: low

#### 2.2 `sphinx_build` return-code is boolean-coerced, masking the actual code

- **Where**: [`runner.py` L285–L288](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L285-L288)
- **What**: `if sphinx_build(self.sphinx_args): raise SphinxBuildError("BUILD FAILED")` coerces the return code to bool. The actual exit code (which Sphinx uses to distinguish warnings-as-errors from hard failures) is discarded.
- **Why it matters**: The error message is always the same string, regardless of whether the failure was a warning promoted to error, a missing extension, or a Python traceback in conf.py.
- **Suggested fix**: Capture `rc = sphinx_build(self.sphinx_args)` and include it in the error: `raise SphinxBuildError(f"BUILD FAILED (exit code {rc})")`.
- **Effort**: S
- **Risk**: low

#### 2.3 `HTTPDomain.merge_domaindata` uses `%`-formatting but not `%`-lazy-logging

- **Where**: [`ext/httpdomain.py` L31–L36](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/httpdomain.py#L31-L36)
- **What**: The `logger.warning(...)` call uses `%` string formatting directly in the call (i.e. `'...' % (a, b, c)`). This eagerly constructs the string even when the WARNING level is disabled, and it swallows potential `TypeError`s (wrong number of args) silently.
- **Why it matters**: Minor performance issue; more importantly, if `other_data[entry_point_name][0]` is a non-string type, the `% (typ, ...)` substitution will fail silently.
- **Suggested fix**: Use lazy-logging form: `logger.warning('duplicate HTTP %s method definition %s in %s, other instance is in %s', typ, entry_point_name, ...)`.
- **Effort**: S
- **Risk**: low

#### 2.4 Vendored `sphinx_tabs` carries a module-level startup cost and is untested

- **Where**: [`sphinx_tabs/tabs.py` L23–L26](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/sphinx_tabs/tabs.py#L23-L26)
- **What**: `LEXER_MAP` is populated at import time by iterating all installed Pygments lexers (`get_all_lexers()`). This is an O(N) scan of all lexers every time the module is imported, adding latency to each `sphinx-build` invocation.
- **Why it matters**: On machines with many Pygments plugins this is measurable startup cost; more importantly, there are zero tests for any of the `sphinx_tabs` code, yet it is shipped as part of the package.
- **Suggested fix**: Lazy-initialise `LEXER_MAP` (compute on first use) or remove the vendored copy if the upstream issue ([sphinx-tabs#171](https://github.com/executablebooks/sphinx-tabs/issues/171)) has been resolved. Add at minimum smoke tests for `TabsDirective` and `CodeTabDirective.run()`.
- **Effort**: M
- **Risk**: medium

#### 2.5 `update_config` in `sphinx_tabs/tabs.py` uses runtime `dir(app)` checks for API compatibility

- **Where**: [`sphinx_tabs/tabs.py` L298–L310](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/sphinx_tabs/tabs.py#L298-L310)
- **What**: `if "add_css_file" in dir(app)` / `if "add_script_file" in dir(app)` guards exist to support very old Sphinx versions (pre-3.5) that used `add_stylesheet`/`add_js_file`. `setup.cfg` already requires `sphinx>=7.2.2`, so the old fallback paths are dead.
- **Why it matters**: Dead compatibility shims confuse readers and make the code harder to update.
- **Suggested fix**: Remove the `dir(app)` guards and call `app.add_css_file` / `app.add_script_file` directly.
- **Effort**: S
- **Risk**: low

---

### 3. Async correctness

#### 3.1 `run()` is `async` but every call inside it is blocking sync

- **Where**: [`runner.py` L337–L353](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L337-L353)
- **What**: `run()` is declared `async` and decorated with `@runner.cleansup` and `@runner.catches(...)`, but every statement inside it is a direct synchronous call: `validate_args()`, `check_env()`, `build_summary()`, `build_html()`, and `save_html()`. There is not a single `await` expression.
- **Why it matters**: The entire Sphinx build (which can take 5–30 minutes) runs on the event loop, blocking it for other tasks. Any other coroutines sharing the loop will starve.
- **Suggested fix**: Run the heavy sync operations via `loop.run_in_executor(None, self.build_html)`. Alternatively, since there is no genuine concurrency needed here, drop the `async` facade and restructure around a sync `Runner` base if one is available.
- **Effort**: M
- **Risk**: medium

#### 3.2 `check_env()` performs blocking filesystem reads on the event loop

- **Where**: [`runner.py` L315–L322](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L315-L322)
- **What**: `self.rst_dir.joinpath("version_history", ...).read_text()` is a blocking `open()` + `read()` call inside a function called from `async def run()`, directly on the event loop.
- **Why it matters**: Cascades from finding 3.1 — same root cause, same remedy.
- **Suggested fix**: Same as 3.1 — move sync I/O to a thread pool executor.
- **Effort**: S (once 3.1 is resolved)
- **Risk**: low

---

### 4. Subprocess / filesystem I/O

#### 4.1 `check_env()` leaks `FileNotFoundError` when version-history file is absent

- **Where**: [`runner.py` L313–L318](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L313-L318)
- **What**: `self.rst_dir.joinpath("version_history", minor_version, f"{self.docs_tag}.rst").read_text()` will raise a raw `FileNotFoundError` if the RST file does not exist. The `@runner.catches((SphinxBuildError, SphinxEnvError))` decorator on `run()` does **not** catch `FileNotFoundError`, so the traceback escapes to the top-level caller.
- **Why it matters**: Users see an unhandled Python traceback instead of a clean error message; CI pipelines that key off exit code 1 may fail silently.
- **Suggested fix**:
  ```python
  try:
      version_current = self.rst_dir.joinpath(
          "version_history", minor_version,
          f"{self.docs_tag}.rst").read_text()
  except FileNotFoundError:
      raise SphinxEnvError(
          f"Version history file not found for {self.docs_tag}")
  ```
- **Effort**: S
- **Risk**: low

#### 4.2 `save_html()` destroys the existing output before the new build is verified

- **Where**: [`runner.py` L324–L335](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L324-L335)
- **What**: When `output_path` already exists, `save_html()` unconditionally deletes it (`unlink` or `shutil.rmtree`) before copying / packing the new HTML. If `shutil.copytree` or `utils.pack` subsequently fails, the caller is left with no output at all.
- **Why it matters**: Destructive operations without atomic swap create a window where the output directory is missing; re-running the build may not recover it if the upstream RST sources have also changed.
- **Suggested fix**: Copy/pack to a sibling temp path first, then atomically rename over the destination: `output_path.with_suffix(".new")` → rename to `output_path`.
- **Effort**: M
- **Risk**: medium

#### 4.3 `rst_tar` is a `@cached_property` that always wraps an arg, even when absent

- **Where**: [`runner.py` L199–L202](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L199-L202)
- **What**: `rst_tar` does `return pathlib.Path(self.args.rst_tar)` unconditionally. If `self.args.rst_tar` is an empty string or `None` (e.g. when the positional argument is not supplied), `pathlib.Path("")` produces a path that points to the CWD, not `None`. `rst_dir` then checks `if self.rst_tar:` — but `pathlib.Path("")` is falsy, so extraction is skipped. The discrepancy between "always returns a Path" and "caller checks truthiness" is confusing.
- **Why it matters**: Subtle truthiness semantics of `pathlib.Path` objects lead to confusing behaviour; `pathlib.Path("")` is falsy but still a `Path`, not `None`.
- **Suggested fix**: Return `pathlib.Path(self.args.rst_tar) if self.args.rst_tar else None` and annotate `rst_tar` as `pathlib.Path | None`. Update `rst_dir` to compare `if self.rst_tar is not None`.
- **Effort**: S
- **Risk**: low

---

### 5. Caching / memoisation

#### 5.1 `rst_dir` `@cached_property` performs side-effecting I/O at access time

- **Where**: [`runner.py` L190–L197](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L190-L197)
- **What**: `rst_dir` calls `utils.extract(rst_dir, self.rst_tar)` inside a `@cached_property`. The pattern obscures an expensive, failure-prone side effect (tar extraction) behind a property access.
- **Why it matters**: Readers expect properties to be pure; unexpected I/O in a property makes error-handling harder (where do you catch the `tarfile.TarError`?). If `utils.extract` raises, the cached_property descriptor will cache the exception frame, preventing retry.
- **Suggested fix**: Move the extraction call into an explicit `_extract_rst()` method called once during `run()`, and make `rst_dir` a pure path computation.
- **Effort**: M
- **Risk**: low

#### 5.2 `colors` is `@cached_property` for a trivially cheap dict

- **Where**: [`runner.py` L78–L84](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L78-L84)
- **What**: `colors` constructs a three-key `dict` from `colorama.Fore` constants. There is no I/O, no computation, and no mutability risk — making it `@cached_property` adds a write to `__dict__` for no benefit.
- **Why it matters**: Minor nit, but inconsistency in caching strategy muddies the "why is this cached?" reasoning for future readers.
- **Suggested fix**: Change to a plain `@property`, or better, a class-level constant `_COLORS: dict[str, str]`.
- **Effort**: S
- **Risk**: low

#### 5.3 `config_file` `@cached_property` does a disk write on first access

- **Where**: [`runner.py` L86–L92](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L86-L92)
- **What**: `config_file` calls `utils.to_yaml(...)` — a file-write operation — inside a `@cached_property`. Same concern as 5.1: hidden I/O in a property access.
- **Why it matters**: If `build_dir` does not yet exist, this raises an uncaught `FileNotFoundError` or `PermissionError` at property access time, which is surprising.
- **Suggested fix**: Likewise, move the file-write into an explicit method (e.g. `_write_config()`) called from `run()`, and make `config_file_path` the cached path computation.
- **Effort**: M
- **Risk**: low

---

### 6. Error handling

#### 6.1 `run()` uses `print(e)` for error reporting instead of the framework logger

- **Where**: [`runner.py` L344–L346](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L344-L346), [`runner.py` L349–L351](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L349-L351)
- **What**: Both `SphinxEnvError` and `SphinxBuildError` are caught and reported via bare `print(e)`, bypassing `self.log` (the structured logger provided by `aio.run.runner`). `save_html()` does use `self.log.warning()`, creating an inconsistency.
- **Why it matters**: Errors are not timestamped, have no log level, and will not appear in structured log aggregators. The inconsistency makes it unclear which output channel to watch for failures.
- **Suggested fix**: Replace `print(e)` with `self.log.error(str(e))` to be consistent with the rest of the framework.
- **Effort**: S
- **Risk**: low

#### 6.2 `ValidatingCodeBlock._validate()` loses exception context

- **Where**: [`ext/validating_code_block.py` L60–L68](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/validating_code_block.py#L60-L68)
- **What**: `except (ParseError, KeyError): raise ExtensionError(...)` does not chain the original exception (`raise ... from e`), so the root cause is hidden in tracebacks.
- **Why it matters**: When debugging a validation failure, engineers see only "Failed config validation for type X" without the underlying protobuf parse error message.
- **Suggested fix**:
  ```python
  except (ParseError, KeyError) as e:
      raise ExtensionError(
          f"Failed config validation for type: '{self.options.get('type-name')}' "
          f"in: {source} line: {line}") from e
  ```
- **Effort**: S
- **Risk**: low

#### 6.3 `debug()` context manager always prints timing even on exception

- **Where**: [`runner.py` L26–L36](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L26-L36)
- **What**: The `finally:` block in `debug()` always prints the timing line. When `sphinx_build()` raises (via `SphinxBuildError`), the timing output appears before the error message, cluttering logs.
- **Why it matters**: Cosmetic, but confusing during failure diagnosis. The `# TODO: remove this once build perf work is complete` suggests this is already known dead code.
- **Suggested fix**: Delete `debug()` entirely (the TODO says so) and replace the `with debug(self.jobs):` call in `build_html()` with a direct call to `sphinx_build`.
- **Effort**: S
- **Risk**: low

---

### 7. Configuration / data hygiene

#### 7.1 `py_compatible` checks Python `>= 3.8` but the package requires `>= 3.12`

- **Where**: [`runner.py` L178–L183](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L178-L183), [`setup.cfg` L27](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/setup.cfg#L27)
- **What**: `py_compatible` returns `True` when `sys.version_info.major == 3 and sys.version_info.minor >= 8`. Since `setup.cfg` requires `python_requires = >=3.12`, the guard can never be `False` in a compliant installation — the check is dead code.
- **Why it matters**: The `check_env()` error message still says "must be >= 3.8", giving users a misleading floor version. If someone installs on Python 3.11 via `--ignore-requires-python`, the check passes incorrectly.
- **Suggested fix**: Update the guard to `>= 3.12` to match `setup.cfg`, or remove `py_compatible` / `check_env()`'s version check entirely since `python_requires` in packaging already enforces this.
- **Effort**: S
- **Risk**: low

#### 7.2 `check_env()` error message names wrong file

- **Where**: [`runner.py` L319–L322](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L319-L322)
- **What**: The error message says "not found in version_history/current.rst" but the code actually reads `version_history/{minor_version}/{docs_tag}.rst`.
- **Why it matters**: The wrong filename in the error message sends engineers to look at a file that does not exist and is not involved.
- **Suggested fix**: Update the error message to include the actual path:
  ```python
  f"Git tag ({self.version_number}) not found in "
  f"version_history/{minor_version}/{self.docs_tag}.rst"
  ```
- **Effort**: S
- **Risk**: low

#### 7.3 Envoy docs URL is hard-coded in `intersphinx_mapping`

- **Where**: [`runner.py` L154–L160](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L154-L160)
- **What**: The URL prefix `"https://www.envoyproxy.io/docs/envoy/"` is embedded inline in the `intersphinx_mapping` comprehension.
- **Why it matters**: If the docs URL ever changes, the magic string is invisible to tooling (no grep-for-constant), easy to miss.
- **Suggested fix**: Extract to a module-level constant: `_DOCS_BASE_URL = "https://www.envoyproxy.io/docs/envoy"`.
- **Effort**: S
- **Risk**: low

---

### 8. Logging / observability

#### 8.1 `build_summary()` uses `print()` calls throughout

- **Where**: [`runner.py` L290–L300](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L290-L300)
- **What**: The entire build-config summary is printed with bare `print()` statements. `self.log` is available but not used.
- **Why it matters**: Output goes to stdout rather than through the structured logger; if stdout is redirected or captured (e.g. in CI log aggregators), the summary disappears.
- **Suggested fix**: Use `self.log.info(...)` for each line of the summary so it participates in the framework's logging infrastructure.
- **Effort**: S
- **Risk**: low

#### 8.2 Sphinx warnings are swallowed after `-W --keep-going`

- **Where**: [`runner.py` L205–L217](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L205-L217)
- **What**: `sphinx_args` always includes `-W` (treat warnings as errors) and `--keep-going` (collect all errors before stopping). Sphinx writes all warning details to its own stdout/stderr. After the build fails, `build_html()` raises `SphinxBuildError("BUILD FAILED")` with no reference to which warnings fired.
- **Why it matters**: Engineers must scroll back through potentially large Sphinx output to find the warning that caused the failure; there is no structured record of which warnings were promoted to errors.
- **Suggested fix**: Capture Sphinx stdout/stderr into a `StringIO` buffer and attach the tail to the `SphinxBuildError` message. Alternatively, log the Sphinx output line-by-line through `self.log`.
- **Effort**: M
- **Risk**: low

---

### 9. Type-annotation correctness

#### 9.1 `versions_path` has no return annotation

- **Where**: [`runner.py` L264–L265](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L264-L265)
- **What**: `def versions_path(self):` is the only public property in `SphinxRunner` that lacks a return type annotation. Mypy will infer `pathlib.Path` correctly, but the missing annotation is inconsistent with the rest of the class.
- **Suggested fix**: Add `-> pathlib.Path`.
- **Effort**: S
- **Risk**: low

#### 9.2 `colors` return type is unparameterised `dict`

- **Where**: [`runner.py` L79](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L79)
- **What**: `def colors(self) -> dict:` — should be `dict[str, str]`.
- **Suggested fix**: `-> dict[str, str]`.
- **Effort**: S
- **Risk**: low

#### 9.3 `debug()`, `_color()`, `run()`, and `add_arguments()` lack return annotations

- **Where**: [`runner.py` L27](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L27), [`runner.py` L268](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L268), [`runner.py` L337](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L337), [`runner.py` L362](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L362)
- **What**: Several functions and methods (including the public `run()` coroutine) have no return type annotation.
- **Suggested fix**: Add `-> None` or appropriate types; `run()` should return `-> int | None`, `_color()` → `-> str`, `debug()` → `-> Iterator[None]` (as a contextmanager).
- **Effort**: S
- **Risk**: low

#### 9.4 `# type:ignore` on first-party imports without justification

- **Where**: [`runner.py` L14](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L14), [`runner.py` L16](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L16), [`ext/httpdomain.py` L4–L10](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/httpdomain.py#L4-L10)
- **What**: `colorama`, `sphinx.cmd.build`, `pygments`, and `sphinxcontrib.httpdomain` are suppressed with blanket `# type:ignore`. `setup.cfg` lists `types-pygments` as a type dependency, making the `# type:ignore` on `pygments` imports suspicious — the stubs may already cover these imports.
- **Why it matters**: Blanket ignores hide real type errors that mypy would catch if the stubs were used.
- **Suggested fix**: Test each import with mypy after ensuring stubs are on the path; replace `# type:ignore` with narrower `# type:ignore[import-untyped]` (or remove if stubs exist). Add a comment justifying any that remain.
- **Effort**: S
- **Risk**: low

#### 9.5 `sphinx_tabs/tabs.py` is entirely unannotated

- **Where**: [`sphinx_tabs/tabs.py` L1–L366](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/sphinx_tabs/tabs.py#L1-L366)
- **What**: The vendored tabs module has no type annotations whatsoever — no parameter types, no return types, no class-level attribute annotations. Given the package now includes `py.typed`, mypy will attempt to check this file.
- **Suggested fix**: Add annotations to public functions and the `_FindTabsDirectiveVisitor` class at minimum. Or suppress the file via `# type: ignore` at the module level with a comment explaining it is vendored.
- **Effort**: M
- **Risk**: low

---

### 10. Testing smells

#### 10.1 Tests verify implementation details, not observable behaviour

- **Where**: [`tests/test_sphinx_runner.py` L37–L50](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/tests/test_sphinx_runner.py#L37-L50), throughout the file
- **What**: Almost every test patches the module's internal dependencies (even stdlib like `pathlib`) and then asserts that the patched mock was called with specific arguments. For example, `test_sphinx_runner_build_dir` patches `pathlib` and `SphinxRunner.tempdir` and then asserts `m_plib.Path.call_args == [(m_temp.return_value.name,), {}]` — this just re-states the implementation rather than asserting that the returned `Path` points to the temp directory.
- **Why it matters**: These tests break on any refactoring, even if observable behaviour is preserved. They provide confidence that the code was written correctly once, but not that it continues to work correctly.
- **Suggested fix**: For property tests, prefer functional assertions: create a real `DummySphinxRunner` with a real (or fake) `tempdir` and assert that `build_dir` returns a `pathlib.Path` under a `tmp_path`-like location. Reserve mocking for network I/O and subprocess calls.
- **Effort**: L
- **Risk**: low (tests only)

#### 10.2 `cmd.py` `main()` and `cmd()` have no tests

- **Where**: [`envoy/docs/sphinx_runner/cmd.py` L7–L12](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/cmd.py#L7-L12)
- **What**: The two entry-point functions (`main` and `cmd`) are entirely untested. `cmd()` calls `sys.exit()` which requires careful patching, but `main()` can be tested without it.
- **Suggested fix**: Add `test_cmd_main` that patches `SphinxRunner` and asserts that `SphinxRunner(*args)()` is returned, and `test_cmd_cmd` that patches `sys.exit` and `main`.
- **Effort**: S
- **Risk**: low

#### 10.3 `sphinx_tabs/tabs.py` has zero tests

- **Where**: [`sphinx_tabs/tabs.py`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/sphinx_tabs/tabs.py) — no corresponding test file
- **What**: The vendored sphinx-tabs code (366 lines including four directives) is completely absent from the test suite.
- **Suggested fix**: At minimum test `setup()` wiring and `TabsDirective.run()` with a minimal Sphinx app fixture. If the upstream issue is resolved, removal of the vendored copy is preferable.
- **Effort**: M
- **Risk**: low (tests only)

#### 10.4 `check_env()` test does not cover `FileNotFoundError`

- **Where**: [`tests/test_sphinx_runner.py` L693–L757](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/tests/test_sphinx_runner.py#L693-L757)
- **What**: The parametrised `test_sphinx_runner_check_env` test does not include a case where the version-history RST file is missing (finding 4.1). Mocking `rst_dir.joinpath.return_value.read_text` to raise `FileNotFoundError` would confirm the desired handling.
- **Suggested fix**: Add `@pytest.mark.parametrize("file_missing", [True, False])` to the test and assert `SphinxEnvError` is raised with an appropriate message when `file_missing=True`.
- **Effort**: S
- **Risk**: low (tests only)

#### 10.5 `test_sphinx_runner_run` is `async` without `@pytest.mark.asyncio`

- **Where**: [`tests/test_sphinx_runner.py` L822–L891](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/tests/test_sphinx_runner.py#L822-L891)
- **What**: The test is `async def test_sphinx_runner_run(...)` with no `@pytest.mark.asyncio` decorator. It relies on a conftest or `asyncio_mode = auto` setting in `pytest.ini` / `pyproject.toml`. If that setting is removed or the conftest changes, this test will silently pass without executing the `await runner.run()` line.
- **Suggested fix**: Add explicit `@pytest.mark.asyncio` to the test, or verify that the project-wide `asyncio_mode = auto` is enforced.
- **Effort**: S
- **Risk**: low

---

### 11. Dead / duplicated / commented-out code

#### 11.1 `debug()` timing helper is explicitly marked for removal

- **Where**: [`runner.py` L25–L36](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L25-L36)
- **What**: `# TODO: remove this once build perf work is complete` has been in the codebase for multiple release cycles. The function adds `print()` noise during failure and blocks proper logging. It should be deleted.
- **Suggested fix**: Remove `debug()` and replace `with debug(self.jobs):` in `build_html()` with a direct call.
- **Effort**: S
- **Risk**: low

#### 11.2 Commented-out `pkg_resources` namespace declarations

- **Where**: [`__init__.py` L14](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/__init__.py#L14), [`sphinx_tabs/__init__.py` L3](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/sphinx_tabs/__init__.py#L3)
- **What**: Two files contain `# __import__("pkg_resources").declare_namespace(__name__)` commented out. These are legacy PEP 420 namespace-package declarations that predate `find_namespace:` in `setup.cfg`.
- **Suggested fix**: Delete both commented-out lines.
- **Effort**: S
- **Risk**: low

#### 11.3 `# TODO: Use packaging.version.Version` in `version_number`

- **Where**: [`runner.py` L250](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L250)
- **What**: A TODO comment to use `packaging.version.Version` for `version_number` has never been actioned. `packaging` is already a dependency (used in `docker_image_tag_name`).
- **Suggested fix**: Parse `version_number` with `Version(raw).public` to normalise the string, or at minimum remove the comment if the current string-based approach is intentional.
- **Effort**: S
- **Risk**: low

#### 11.4 `# this should probs only check the first line` in `check_env()`

- **Where**: [`runner.py` L314](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L314)
- **What**: An acknowledged correctness concern ("probs" is "probably") has never been addressed. The code currently reads the entire file and checks `if self.version_number not in version_current`, which is a substring match on the full file.
- **Suggested fix**: Either fix it (read only the first line) or add a test case that proves the full-file search is intentional. Remove the comment either way.
- **Effort**: S
- **Risk**: low

---

### 12. Documentation

#### 12.1 `release_level` has a copy-pasted, completely wrong docstring

- **Where**: [`runner.py` L185–L188](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L185-L188)
- **What**: `release_level` has docstring `"""Current python version is compatible."""` — copy-pasted from `py_compatible` directly above it. The property has nothing to do with Python compatibility.
- **Suggested fix**: `"""Release level: 'tagged' for versioned releases, 'pre-release' otherwise."""`
- **Effort**: S
- **Risk**: low

#### 12.2 `versions_path` has no docstring

- **Where**: [`runner.py` L264–L265](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L264-L265)
- **What**: `versions_path` is the only cached property with no docstring.
- **Suggested fix**: `"""Path to versions.yaml within the extracted RST directory."""`
- **Effort**: S
- **Risk**: low

#### 12.3 `README.rst` contains only a one-sentence description

- **Where**: [`README.rst`](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/README.rst)
- **What**: The README has no usage instructions, no list of CLI arguments, no description of how `ENVOY_DOCS_BUILD_CONFIG` is used, and no mention of the custom Sphinx extensions shipped with the package.
- **Why it matters**: New contributors or integrators have no starting point without reading the source.
- **Suggested fix**: Add a "Usage" section showing the CLI invocation, the main `--` flags, and a note about the bundled extensions (`validated-code-block`, `httpdomain`, `sphinx_tabs`).
- **Effort**: M
- **Risk**: low

#### 12.4 No module-level docstrings anywhere

- **Where**: [`runner.py` L1](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py#L1), [`ext/httpdomain.py` L1](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/httpdomain.py#L1), [`ext/validating_code_block.py` L1](https://github.com/envoyproxy/toolshed/blob/5bd5e4fbea8fcfe14418c9381a4abcaefb6e7ef9/py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/validating_code_block.py#L1)
- **What**: None of the source modules have a module-level docstring explaining purpose, usage, or relationship to other modules.
- **Suggested fix**: Add one-line module docstrings to `runner.py`, `ext/httpdomain.py`, `ext/validating_code_block.py`, and `ext/powershell_lexer.py`.
- **Effort**: S
- **Risk**: low

---

## Recommended follow-up PRs

1. **Fix escaped errors and wrong error message** — Wrap the `FileNotFoundError` in `check_env()` as `SphinxEnvError` (finding 4.1), fix the wrong filename in the error message (7.2), add the missing test case (10.4), and fix the `py_compatible` floor version (7.1). Bundles findings 4.1, 6.1, 7.1, 7.2, 10.4. Effort **S**. Risk **low**.

2. **Delete dead code and fix commenting** — Remove `debug()` and its `# TODO` (finding 11.1), delete `_build_dir` class variable (1.2), remove commented-out `pkg_resources` lines (11.2), fix `release_level` docstring (12.1), add `versions_path` docstring (12.2), fix `# this should probs…` (11.4), fix `# TODO: Use packaging.version.Version` (11.3). Bundles findings 1.2, 6.3, 11.1–11.4, 12.1–12.2. Effort **S**. Risk **low**.

3. **Type annotation and `type:ignore` cleanup** — Add return types to `versions_path`, `colors`, `debug()`, `_color()`, `run()`, `add_arguments()` (findings 9.1–9.3), scope or remove `# type:ignore` comments (9.4), add annotations to public functions in `sphinx_tabs/tabs.py` (9.5), move `intersphinx_mapping` to `BaseConfigDict` (1.4). Bundles findings 1.4, 9.1–9.5. Effort **S**. Risk **low**.

4. **Replace `print()` with structured logging** — Replace all `print(e)` in `run()` with `self.log.error()` (6.1), replace `print()` in `build_summary()` with `self.log.info()` (8.1), add exception chaining in `ValidatingCodeBlock._validate()` (6.2), include the actual sphinx return code in `SphinxBuildError` (2.2), fix the `%`-formatting in `httpdomain.py` logger call (2.3). Bundles findings 2.2, 2.3, 6.1, 6.2, 8.1. Effort **S**. Risk **low**.

5. **Fix minor Sphinx integration issues** — Rename `html_dir` → `output_dir` derived from `build_target` (2.1), add the `DOCS_BASE_URL` constant (7.3), fix `rst_tar` truthiness and `None` typing (4.3), remove dead `dir(app)` compat guards in `sphinx_tabs/tabs.py` (2.5). Bundles findings 2.1, 2.5, 4.3, 7.3. Effort **S**. Risk **low**.

6. **Fix caching anti-patterns** — Move `utils.extract()` from `rst_dir` property to an explicit `_extract_rst()` call in `run()` (5.1), move `utils.to_yaml()` from `config_file` property to an explicit `_write_config()` call (5.3), make `colors` a class constant or plain `@property` (5.2), and make `save_html()` write to a temp path before atomic rename (4.2). Bundles findings 4.2, 5.1, 5.2, 5.3. Effort **M**. Risk **low**.

7. **Move blocking sync calls off the event loop** — Run `build_html()`, `check_env()`, `save_html()`, and other blocking calls via `loop.run_in_executor(None, ...)` inside `run()`, or adopt a sync runner base class if one is available in `aio.run.runner`. Bundles findings 3.1, 3.2. Effort **M**. Risk **medium**.

8. **Add missing tests and improve test quality** — Add tests for `cmd.py` entry points (10.2), add smoke tests for `sphinx_tabs/tabs.py` (10.3), add `@pytest.mark.asyncio` to `test_sphinx_runner_run` (10.5), and replace the most egregiously implementation-mirroring unit tests with behavioural assertions (10.1). Bundles findings 10.1–10.5. Effort **L**. Risk **low**.
