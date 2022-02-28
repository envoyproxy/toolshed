
import asyncio
import pathlib
import shutil
import subprocess as subprocess
from concurrent import futures
from functools import cached_property, partial
from typing import (
    AsyncIterator, Dict, Iterable, List, Optional,
    Pattern, Set, Tuple, Type, Union)

import abstracts

from aio.core import event, subprocess as _subprocess
from aio.core.functional import async_property, async_set, AwaitableGenerator


GREP_MIN_BATCH_SIZE = 500
GREP_MAX_BATCH_SIZE = 2000


@abstracts.implementer(_subprocess.ISubprocessHandler)
class ADirectoryGrepper(
        _subprocess.ASubprocessHandler,
        metaclass=abstracts.Abstraction):
    """Blocking directory grepper.

    Run inside a subproc, so *must* be picklable.
    """

    @classmethod
    def include_path(cls, path: str, path_matcher, exclude_matcher) -> bool:
        return bool(
            path
            and (not path_matcher
                 or path_matcher.match(path))
            and (not exclude_matcher
                 or not exclude_matcher.match(path)))

    def __init__(
            self,
            path: str,
            path_matcher: Optional[Pattern[str]] = None,
            exclude_matcher:  Optional[Pattern[str]] = None) -> None:
        _subprocess.ASubprocessHandler.__init__(self, path)
        self.path_matcher = path_matcher
        self.exclude_matcher = exclude_matcher

    def handle(self, response: subprocess.CompletedProcess) -> Set[str]:
        return set(
            path
            for path
            in response.stdout.split("\n")
            if self.include_path(
                path,
                self.path_matcher,
                self.exclude_matcher))

    def handle_error(
            self,
            response: subprocess.CompletedProcess) -> Dict[str, List[str]]:
        # TODO: Handle error in directory class
        return super().handle_error(response)


@abstracts.implementer(event.IExecutive)
class ADirectory(event.AExecutive, metaclass=abstracts.Abstraction):
    """A filesystem directory, with an associated fileset, and tools for
    finding files.

    The required `path` argument should be the path to an existing filesystem
    directory.

    The `exclude` and `exclude_dirs` parameters are passed to the `grep`
    command as `--exclude` and `--exclude-dir` args respectively.

    You can specify inclusive and exclusive regex matchers with `path_matcher`
    and `exclude_matcher`.

    By default, only text files (from grep/git grep pov) will be searched,
    you can override this by setting `text_only` to `False`.
    """

    def __init__(
            self,
            path: Union[str, pathlib.Path],
            exclude: Optional[Iterable[str]] = None,
            exclude_dirs: Optional[Iterable[str]] = None,
            path_matcher: Optional[Pattern[str]] = None,
            exclude_matcher: Optional[Pattern[str]] = None,
            text_only: Optional[bool] = True,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            pool: Optional[futures.Executor] = None) -> None:
        self._path = path
        self.path_matcher = path_matcher
        self.exclude_matcher = exclude_matcher
        self.text_only = text_only
        self.exclude = exclude or ()
        self.exclude_dirs = exclude_dirs or ()
        self._loop = loop
        self._pool = pool

    @cached_property
    def absolute_path(self) -> str:
        return str(self.path.resolve())

    @property  # type:ignore
    @abstracts.interfacemethod
    def directory_grepper_class(self) -> Type[ADirectoryGrepper]:
        raise NotImplementedError

    @async_property(cache=True)
    async def files(self) -> Set[str]:
        """Set of relative file paths associated with this directory."""
        return await self.get_files()

    @cached_property
    def grep_args(self) -> Tuple[str, ...]:
        """Default args to pass when calling `grep`."""
        return (
            *self.grep_command_args,
            *(("-I", )
              if self.text_only
              else ()),
            *self.grep_exclusion_args)

    @property
    def grep_command_args(self) -> Tuple[str, ...]:
        """Path args for the `grep` command."""
        grep_command = shutil.which("grep")
        if grep_command:
            return grep_command, "-r"
        raise _subprocess.exceptions.OSCommandError(
            "Unable to find `grep` command")

    @property
    def grep_exclusion_args(self) -> Tuple[str, ...]:
        """Grep flags to exclude paths and directories."""
        return (
            tuple(
                f"--exclude={exclusion}"
                for exclusion
                in self.exclude)
            + tuple(
                f"--exclude-dir={directory}"
                for directory
                in self.exclude_dirs))

    @property
    def grep_max_batch_size(self) -> int:
        return GREP_MAX_BATCH_SIZE

    @property
    def grep_min_batch_size(self) -> int:
        return GREP_MIN_BATCH_SIZE

    @cached_property
    def grepper(self) -> ADirectoryGrepper:
        return self.directory_grepper_class(
            str(self.path),
            path_matcher=self.path_matcher,
            exclude_matcher=self.exclude_matcher)

    @cached_property
    def path(self) -> pathlib.Path:
        """Path to this directory."""
        return pathlib.Path(self._path)

    @cached_property
    def shell(self) -> _subprocess.AAsyncShell:
        """Shell that uses the directory path as `cwd`."""
        return _subprocess.AsyncShell(
            cwd=self.path,
            loop=self.loop,
            pool=self.pool)

    async def get_files(self) -> Set[str]:
        return await self.grep(["-l"], "")

    def grep(
            self,
            args: Iterable,
            target: Union[str, Iterable[str]]) -> AwaitableGenerator:
        return AwaitableGenerator(
            self._grep(args, target),
            collector=async_set)

    def parse_grep_args(
            self,
            args: Iterable[str],
            target: Union[
                str,
                Iterable[str]]) -> Tuple[Tuple[str, ...], Iterable[str]]:
        """Parse `grep` args with the defaults to pass to the `grep`
        command."""
        return (
            (*self.grep_args,
             *args),
            ((target, )
             if isinstance(target, str)
             else target))

    def _batched_grep(
            self,
            grep_args: Tuple[str, ...],
            paths: Iterable[str]) -> AwaitableGenerator:
        return self.execute_in_batches(
            partial(self.grepper, *grep_args),
            *paths,
            min_batch_size=self.grep_min_batch_size,
            max_batch_size=self.grep_max_batch_size)

    async def _grep(
            self,
            args: Iterable[str],
            target: Union[str, Iterable[str]]) -> AsyncIterator[str]:
        """Run `grep` in the directory."""
        if not isinstance(target, str) and not target:
            return
        batches = self._batched_grep(
            *self.parse_grep_args(args, target))
        async for batch in batches:
            for result in batch:
                yield result


class AGitDirectory(ADirectory):
    """A filesystem directory, with an associated fileset, and tools for
    finding files.

    Uses the `git` index cache for faster grepping.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.changed = kwargs.pop("changed", None)
        super().__init__(*args, **kwargs)

    @async_property(cache=True)
    async def changed_files(self) -> Set[str]:
        """Files that have changed since `self.changed`, which can be the name
        of a git object (branch etc) or a commit hash."""
        # TODO: move filtering into a subshell
        return set(
            path
            for path
            in await self.shell(
                [self.git_command,
                 "diff",
                 "--name-only",
                 self.changed,
                 "--diff-filter=ACMR",
                 "--ignore-submodules=all"])
            if (path
                and self.directory_grepper_class.include_path(
                    path,
                    self.path_matcher,
                    self.exclude_matcher)))

    @async_property(cache=True)
    async def files(self) -> Set[str]:
        return (
            await self.get_files()
            if not self.changed
            else await self.get_changed_files())

    @property
    def git_command(self) -> str:
        """Path to the `git` command."""
        git_command = shutil.which("git")
        if git_command:
            return git_command
        raise _subprocess.exceptions.OSCommandError(
            "Unable to find the `git` command")

    @property
    def grep_command_args(self) -> Tuple[str, ...]:
        return self.git_command, "grep", "--cached"

    async def get_changed_files(self) -> Set[str]:
        """Files that have changed."""
        # If the super `files` are going to be filtered fetch them first, and
        # only check `changed_files` if there are any matching. Otherwise do
        # the reverse - get the `changed_files` and bail if there are none.
        files = None
        if self.path_matcher or self.exclude_matcher:
            files = await self.get_files()
            if not files:
                return set()
        elif not await self.changed_files:
            return set()
        return (
            (await self.get_files()
             if files is None
             else files)
            & await self.changed_files)
