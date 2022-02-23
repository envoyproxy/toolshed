
import asyncio
import os
import logging
import pathlib
import shutil
import subprocess as _subprocess
from concurrent import futures
from functools import cached_property, lru_cache, partial
from typing import (
    AsyncIterator, Iterable, Optional,
    Pattern, Set, Tuple, Union)

import psutil

import abstracts

from aio.core import event, subprocess
from aio.core.functional import async_property, async_set, AwaitableGenerator
from aio.core.subprocess import exceptions as subprocess_exceptions


logger = logging.getLogger(__name__)

GREP_MIN_BATCH_SIZE = 100
GREP_MAX_BATCH_SIZE = 500


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

    @classmethod
    # @lru_cache(maxsize=None)
    def make_path_absolute(cls, absolute_path, path: str) -> str:
        """Make a directory-relative path absolute."""
        return os.path.join(absolute_path, path)

    @classmethod
    def run_grep(cls, path: str, *args):
        """Run shellcheck command with a list of files from a path."""
        logger.debug(
            f"Running shellcheck (cpu: "
            f"{psutil.Process(os.getpid()).cpu_num()}) on {len(args)} files")
        return cls.handle_grep_response(
            _subprocess.run(
                args,
                cwd=path,
                capture_output=True,
                encoding="utf-8"))

    @classmethod
    def handle_grep_response(cls, response):
        return [x for x in response.stdout.split("\n") if x]

    @classmethod
    def _make_paths_absolute(cls, path: str, paths: Iterable[str]) -> Set[str]:
        """Make directory-relative paths absolute."""
        return set(
            cls.make_path_absolute(path, p)
            for p
            in paths)

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
        self._pool = None  # pool

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
        raise subprocess_exceptions.OSCommandError(
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

    @cached_property
    def path(self) -> pathlib.Path:
        """Path to this directory."""
        return pathlib.Path(self._path)

    @cached_property
    def shell(self) -> subprocess.AAsyncShell:
        """Shell that uses the directory path as `cwd`."""
        return subprocess.AsyncShell(
            cwd=self.path,
            loop=self.loop,
            pool=self.pool)

    @cached_property
    def absolute_path(self):
        return str(self.path.resolve())

    async def get_files(self) -> Set[str]:
        return await self.grep(["-l", ""])

    def grep(
            self,
            args: Iterable,
            target: Optional[str] = None) -> AwaitableGenerator:
        return AwaitableGenerator(
            self._grep(args, target),
            collector=async_set,
            predicate=self._include_file)

    async def make_paths_absolute(self, paths: Iterable[str]) -> Set[str]:
        """Make directory-relative paths absolute."""
        # TODO: only shell out if the number is large
        return await self.execute(
            self._make_paths_absolute,
            self.absolute_path,
            paths)

    def parse_grep_args(
            self,
            args: Iterable[str],
            target: Optional[str] = None) -> Tuple[str, ...]:
        """Parse `grep` args with the defaults to pass to the `grep`
        command."""
        return (
            *self.grep_args,
            *args,
            *((target, )
              if target is not None
              else ()))

    @lru_cache
    def relative_path(self, path: str) -> str:
        """Make an absolute path directory-relative."""
        return path[len(self.absolute_path) + 1:]

    def relative_paths(self, paths: Iterable[str]) -> Set[str]:
        """Make absolute paths directory-relative."""
        return set(
            self.relative_path(path)
            for path
            in paths)

    async def _grep(
            self,
            args: Iterable,
            target: Optional[str] = None) -> AsyncIterator[str]:
        """Run `grep` in the directory."""
        *grep_args, target = self.parse_grep_args(args, target)
        if target:
            batches = self.execute_in_batches(
                partial(self.run_grep, str(self.path), *grep_args),
                *target,
                concurrency=6,
                min_batch_size=GREP_MIN_BATCH_SIZE,
                max_batch_size=GREP_MAX_BATCH_SIZE)
            async for batch in batches:
                for result in batch:
                    yield result
            return
        results = await self.execute(
            partial(
                self.run_grep, str(self.path),
                *grep_args, target))
        for result in results:
            yield result

    @lru_cache
    def _include_file(self, path: str) -> bool:
        return bool(
            (not self.path_matcher
             or self.path_matcher.match(path))
            and (not self.exclude_matcher
                 or not self.exclude_matcher.match(path)))


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
            if (path and self._include_file(path)))

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
        raise subprocess_exceptions.OSCommandError(
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
