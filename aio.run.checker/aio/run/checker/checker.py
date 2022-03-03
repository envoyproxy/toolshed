import argparse
import asyncio
import pathlib
import time
from functools import cached_property
from typing import (
    Awaitable, Callable, Dict, Iterable, List, Optional, Sequence,
    Set, Tuple, Type)

from aio.run import runner


_sentinel = object()


class Checker(runner.Runner):
    """Runs check methods prefixed with `check_` and named in `self.checks`

    Check methods should call the `self.warn`, `self.error` or
    `self.succeed` depending upon the outcome of the checks.
    """
    _active_check = ""
    checks: Tuple[str, ...] = ()

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.success: Dict = {}
        self.errors: Dict = {}
        self.warnings: Dict = {}

    @property
    def active_check(self) -> str:
        """Currently active check."""
        return self._active_check

    @cached_property
    def checks_to_run(self) -> Sequence[str]:
        """Checks to run after being filtered according to CLI args."""
        return self.get_checks()

    @property
    def diff(self) -> bool:
        """Flag to determine whether the checker should print diffs to the
        console."""
        return self.args.diff

    @cached_property
    def disabled_checks(self) -> Dict[str, str]:
        """Checks which have been disabled due to missing CLI args."""
        return {}

    @property
    def error_count(self) -> int:
        """Count of all errors found."""
        return sum(len(e) for e in self.errors.values())

    @property
    def exiting(self) -> bool:
        return "exiting" in self.errors

    @property
    def fail_on_warn(self) -> bool:
        """Return failure when warnings are generated."""
        return self.args.warning == "error"

    @property
    def failed(self) -> dict:
        """Dictionary of errors per check."""
        return dict((k, (len(v))) for k, v in self.errors.items())

    @property
    def fix(self) -> bool:
        """Flag to determine whether the checker should attempt to fix found
        problems."""
        return self.args.fix

    @property
    def has_failed(self) -> bool:
        """Shows whether there are any failures."""
        return bool(
            self.failed
            or (self.warned and self.fail_on_warn))

    @cached_property
    def path(self) -> pathlib.Path:
        """The "path" - usually Envoy src dir. This is used for finding "
        configs for the tooling and should be a dir
        """
        try:
            path = pathlib.Path(self.args.path or self.args.paths[0])
        except IndexError:
            raise self.parser.error(
                "Missing path: `path` must be set either as an arg or with "
                "--path")
        if not path.is_dir():
            raise self.parser.error(
                "Incorrect path: `path` must be a directory, set either as "
                "first arg or with --path")
        return path

    @property
    def paths(self) -> list:
        """List of paths to apply checks to."""
        return self.args.paths or [self.path]

    @property
    def show_summary(self) -> bool:
        """Show a summary at the end or not."""
        return bool(
            not self.exiting
            and (self.args.summary
                 or self.error_count
                 or self.warning_count))

    @property
    def status(self) -> dict:
        """Dictionary showing current success/warnings/errors."""
        return dict(
            success=self.success_count,
            errors=self.error_count,
            warnings=self.warning_count,
            failed=self.failed,
            warned=self.warned,
            succeeded=self.succeeded)

    @property
    def succeeded(self) -> dict:
        """Dictionary of successful checks grouped by check type."""
        return dict((k, (len(v))) for k, v in self.success.items())

    @property
    def success_count(self) -> int:
        """Current count of successful checks."""
        return sum(len(e) for e in self.success.values())

    @cached_property
    def summary(self) -> "CheckerSummary":
        """Instance of the checker's summary class."""
        return self.summary_class(self)

    @property
    def summary_class(self) -> Type["CheckerSummary"]:
        """Checker's summary class."""
        return CheckerSummary

    @property
    def warned(self) -> dict:
        """Dictionary of warned checks grouped by check type."""
        return dict((k, (len(v))) for k, v in self.warnings.items())

    @property
    def warning_count(self) -> int:
        """Current count of warned checks."""
        return sum(len(e) for e in self.warnings.values())

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments to the arg parser."""
        super().add_arguments(parser)
        parser.add_argument(
            "--fix",
            action="store_true",
            default=False,
            help="Attempt to fix in place")
        parser.add_argument(
            "--diff",
            action="store_true",
            default=False,
            help="Display a diff in the console where available")
        parser.add_argument(
            "--warning",
            "-w",
            choices=["warn", "error"],
            default="warn",
            help="Handle warnings as warnings or errors")
        parser.add_argument(
            "--summary",
            action="store_true",
            default=False,
            help="Show a summary of check runs")
        parser.add_argument(
            "--summary-errors",
            type=int,
            default=5,
            help="Number of errors to show in the summary, -1 shows all")
        parser.add_argument(
            "--summary-warnings",
            type=int,
            default=5,
            help="Number of warnings to show in the summary, -1 shows all")
        parser.add_argument(
            "--check",
            "-c",
            choices=self.checks,
            nargs="*",
            help=(
                "Specify which checks to run, can be specified for multiple "
                "checks"))
        for check in self.checks:
            parser.add_argument(
                f"--config-{check}",
                default="",
                help=f"Custom configuration for the {check} check")
        parser.add_argument(
            "--path",
            "-p",
            default=None,
            help=(
                "Path to the test root (usually Envoy source dir). If not "
                "specified the first path of paths is used"))
        parser.add_argument(
            "paths",
            nargs="*",
            help=(
                "Paths to check. At least one path must be specified, or the "
                "`path` argument should be provided"))

    def error(
            self,
            name: str,
            errors: Optional[Iterable[str]],
            log: bool = True,
            log_type: str = "error") -> int:
        """Record (and log) errors for a check type."""
        if not errors:
            return 0
        self.errors[name] = self.errors.get(name, [])
        self.errors[name].extend(errors)
        if not log:
            return 1
        for message in errors:
            getattr(self.log, log_type)(f"[{name}] {message}")
        return 1

    def exit(self) -> int:
        super().exit()
        return self.error("exiting", ["Keyboard exit"], log_type="fatal")

    def get_checks(self) -> Sequence[str]:
        """Get list of checks for this checker class filtered according to user
        args."""
        # Checks filtered according to args
        checks = (
            self.checks
            if not self.args.check
            else [
                check
                for check
                in self.args.check
                if check in self.checks])

        # Filter disabled checks
        for check, reason in self.disabled_checks.items():
            if check not in checks:
                continue
            msg = f"Cannot run disabled check ({check}): {reason}"
            if self.args.check:
                # If user specified a check but it has been
                # disabled, error
                self.error(check, [msg])
            else:
                self.log.notice(msg)

        # error if no checks ?
        return [
            check
            for check
            in checks
            if check not in self.disabled_checks]

    async def on_check_begin(self, check: str) -> None:
        self._active_check = check
        self.log.notice(f"[{check}] Running check...")

    async def on_check_run(self, check: str) -> None:
        """Callback hook called after each check run."""
        self._active_check = ""
        if self.exiting:
            return
        elif check in self.errors:
            self.log.error(f"[{check}] Check failed")
        elif check in self.warnings:
            self.log.warning(f"[{check}] Check has warnings")
        elif check not in self.success:
            self.log.notice(f"[{check}] No checks ran")
        else:
            self.log.notice(
                f"[{check}] Checks ({len(self.success[check])}) "
                "completed successfully")

    async def on_checks_begin(self) -> None:
        """Callback hook called before all checks."""
        # Set up preload tasks
        asyncio.create_task(self.preload())
        self._notify_checks()
        self._notify_preload()

    async def on_checks_complete(self) -> int:
        """Callback hook called after all checks have run, and returning the
        final outcome of a checks_run."""
        if self.show_summary:
            self.summary.print_summary()
        return 1 if self.has_failed else 0

    async def on_runner_error(self, e: BaseException) -> int:
        return await self.on_checks_complete()

    def succeed(self, name: str, success: list, log: bool = True) -> None:
        """Record (and log) success for a check type."""
        self.success[name] = self.success.get(name, [])
        self.success[name].extend(success)
        if not log:
            return
        for message in success:
            self.log.success(f"[{name}] \N{heavy check mark} {message}")

    def warn(self, name: str, warnings: list, log: bool = True) -> None:
        """Record (and log) warnings for a check type."""
        self.warnings[name] = self.warnings.get(name, [])
        self.warnings[name].extend(warnings)
        if not log:
            return
        for message in warnings:
            self.log.warning(f"[{name}] {message}")

    @cached_property
    def check_queue(self) -> asyncio.Queue:
        """Queue of checks to run."""
        return asyncio.Queue()

    @cached_property
    def completed_checks(self) -> Set[str]:
        """Checks that have succesfully completed."""
        return set()

    @cached_property
    def preload_checks(self) -> Dict[str, List[str]]:
        """Mapping of checks to blocking preload tasks."""
        checks: Dict[str, List[str]] = {}
        for name, task in self.preload_checks_data.items():
            for check in task.get("blocks", []):
                checks[check] = checks.get(check, [])
                checks[check].append(name)
        return checks

    @cached_property
    def preload_checks_data(self) -> Dict[str, Dict]:
        return dict(getattr(self, "_preload_checks_data", ()))

    @cached_property
    def preload_pending_tasks(self) -> Set[str]:
        """Currently pending preload tasks."""
        return set()

    @cached_property
    def preload_tasks(self) -> Tuple[Awaitable, ...]:
        """Tuple of awaitables for preloading check data."""
        tasks = [
            self.preload_data(name)
            for name
            in self.preload_checks_data]
        return tuple(t for t in tasks if t)

    @cached_property
    def preloaded_checks(self) -> Set[str]:
        """Checks for wich all preload tasks are complete."""
        return set()

    @property
    def remaining_checks(self) -> Tuple[str, ...]:
        return tuple(
            check
            for check
            in self.checks_to_run
            if (check not in self.removed_checks
                and check not in self.completed_checks))

    @cached_property
    def removed_checks(self) -> Set[str]:
        """Checks removed due to failed preload tasks."""
        return set()

    async def begin_checks(self) -> None:
        """Start the checks queue, and preloaders, and populate the queue with
        any checks that don't require preloaded data."""
        await self.on_checks_begin()
        # Place all checks that are not blocked in the queue.
        for check in self.checks_to_run:
            if check not in self.preload_checks:
                await self.check_queue.put(check)

    async def on_preload(self, task: str) -> None:
        """Event fired after each preload task completes."""
        self.preload_pending_tasks.remove(task)
        for check in self.checks_to_run:
            if self._check_should_run(check):
                self.log.debug(f"Check data preloaded: {check}")
                self.preloaded_checks.add(check)
                await self.check_queue.put(check)
        if self.removed_checks and not self.preload_pending_tasks:
            await self.on_preload_errors()

    async def on_preload_errors(self) -> None:
        """All preloads have completed, and some failed."""
        failed_checks = len(self.removed_checks)
        all_checks = len(self.checks_to_run)
        if failed_checks < all_checks:
            self.log.error(
                "Some checks "
                f"({failed_checks}/{all_checks}) "
                "were not run as required data failed to load")
        else:
            self.log.error(
                f"All ({all_checks}) checks failed as required "
                "data failed to load")
        if not self.remaining_checks:
            await self.check_queue.put(_sentinel)

    async def on_preload_task_failed(
            self,
            task: str,
            e: BaseException) -> None:
        """Preload task failed, disabled related checks."""
        for check in self.preload_checks_data[task]["blocks"]:
            if check in self.removed_checks:
                continue
            # disable any checks that depend upon this task
            self.removed_checks.add(check)
            self.error(
                check,
                [f"Check disabled: data download ({task}) failed {e}"])

    async def preload(self) -> None:
        """Async preload data for checks."""
        # TODO: factor out the preloading to a separate interface
        if self.preload_tasks:
            await asyncio.gather(*self.preload_tasks)

    def preload_data(
            self,
            task: str) -> Optional[Awaitable]:
        """Return an awaitable preload task if required."""
        if self._task_should_preload(task):
            self.preload_pending_tasks.add(task)
            return self.preloader(
                task,
                self.preload_checks_data[task]["fun"](self))

    async def preloader(self, task: str, runner: Awaitable) -> None:
        """Wrap a preload task with the pending queue, and trigger `on_preload`
        event on completion."""
        start = time.time()
        self.log.debug(f"Preloading {task}...")
        proceed = False
        try:
            await runner
        except self.preloader_catches(task) as e:
            self.log.debug(f"Preload failed {task} in {time.time() - start}s")
            await self.on_preload_task_failed(task, e)
            proceed = True
        else:
            self.log.debug(f"Preloaded {task} in {time.time() - start}s")
            proceed = True
        finally:
            if proceed:
                await self.on_preload(task)

    def preloader_catches(self, task: str) -> Tuple[Type[BaseException], ...]:
        return tuple(self.preload_checks_data[task].get("catches", ()))

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

    def _check_should_run(self, check: str) -> bool:
        """Indicate whether a check is ready to run."""
        return bool(
            check in self.preload_checks
            and check not in self.preloaded_checks
            and check not in self.removed_checks
            and not any(
                task
                in self.preload_pending_tasks
                for task in self.preload_checks[check]))

    def _notify_checks(self) -> None:
        checks = ", ".join(self.checks_to_run)
        self.log.notice(f"Running checks: {checks}")

    def _notify_preload(self) -> None:
        preload = ", ".join(
            d
            for d
            in self.checks_to_run
            if d in self.preload_checks)
        if preload:
            self.log.notice(f"Preloading: {preload}")

    async def _run_check(self, check: str) -> None:
        await self.on_check_begin(check)
        await getattr(self, f"check_{check}")()
        await self.on_check_run(check)

    async def _run_from_queue(self) -> None:
        while True:
            if not self.remaining_checks:
                break
            check = await self.check_queue.get()
            if check is _sentinel:
                break
            await self._run_check(check)
            self.check_queue.task_done()
            self.completed_checks.add(check)

    def _task_should_preload(
            self,
            task: str) -> bool:
        handler = self.preload_checks_data[task]
        return not (
            task in self.preload_pending_tasks
            or not any(
                c in self.checks_to_run
                for c
                in handler.get("when", []))
            or any(
                c in self.checks_to_run
                for c
                in handler.get("unless", [])))


class CheckerSummary(object):
    """Summary of completed checks."""

    def __init__(self, checker: Checker) -> None:
        # TODO: factor out the checker object
        self.checker = checker

    @property
    def max_errors(self) -> int:
        """Maximum errors to display in summary."""
        return self.checker.args.summary_errors

    @property
    def max_warnings(self) -> int:
        """Maximum warnings to display in summary."""
        return self.checker.args.summary_warnings

    def max_problems_of(self, problem_type: str, n: int) -> int:
        """Max of `n` and global max for number of items to display for a given
        problem type."""
        global_max = getattr(self, f"max_{problem_type}")
        return (
            min(n, global_max)
            if global_max >= 0
            else n)

    def print_failed(self, problem_type: str) -> None:
        """Print failures of a given problem_type - eg error, warning."""
        for check, problems in getattr(self.checker, problem_type).items():
            self.print_failed_check(problem_type, check, problems)

    def print_failed_check(
            self,
            problem_type: str,
            check: str,
            problems: List[str]) -> None:
        """Summary for a failed check of a given problem type."""
        self.writer_for(problem_type)(
            self.problem_section(problem_type, check, problems))

    def print_status(self) -> None:
        """Print summary status to stderr."""
        if self.checker.errors:
            self.checker.log.error(f"{self.checker.status}")
        elif self.checker.warnings:
            self.checker.log.warning(f"{self.checker.status}")
        else:
            self.checker.log.info(f"{self.checker.status}")

    def print_summary(self) -> None:
        """Write summary to stderr."""
        self.print_failed("warnings")
        self.print_failed("errors")
        self.print_status()

    def problem_section(
            self,
            problem_type: str,
            check: str,
            problems: List[str]) -> str:
        """Print a summary section."""
        max_display = self.max_problems_of(problem_type, len(problems))
        title = self.problem_title(problem_type, len(problems), max_display)
        lines = problems[:max_display]
        section = [
            f"{problem_type.upper()} Summary [{check}]{title}",
            "-" * 80]
        if lines:
            section += [line.split("\n")[0] for line in lines]
        return "\n".join(section + [""])

    def problem_title(
            self,
            problem_type: str,
            n: int,
            max_display: int) -> str:
        """Problem summary title for a check."""
        return (
            f": (showing first {max_display} of {n})"
            if (n > max_display and max_display > 0)
            else ":")

    def writer_for(self, problem_type: str) -> Callable:
        """Write for a particular problem type."""
        return (
            self.checker.log.notice
            if problem_type == "warnings"
            else self.checker.log.error)
