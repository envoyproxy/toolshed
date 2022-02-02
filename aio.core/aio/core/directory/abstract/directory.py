import pathlib
import shutil
from functools import cached_property, lru_cache
from typing import (
    AsyncIterator, Iterable, Optional,
    Pattern, Set, Tuple, Union)

import abstracts

from aio.core import subprocess
from aio.core.functional import async_property, async_set, AwaitableGenerator
from aio.core.subprocess import exceptions as subprocess_exceptions


class ADirectory(metaclass=abstracts.Abstraction):
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
            text_only: Optional[bool] = True) -> None:
        self._path = path
        self.path_matcher = path_matcher
        self.exclude_matcher = exclude_matcher
        self.text_only = text_only
        self.exclude = exclude or ()
        self.exclude_dirs = exclude_dirs or ()

    @async_property(cache=True)
    async def files(self) -> Set[str]:
        """Set of relative file paths associated with this directory."""
        return await self.grep(["-l", ""])

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
        return subprocess.AsyncShell(cwd=self.path)

    @lru_cache(maxsize=None)
    def absolute_path(self, path: str) -> str:
        """Make a directory-relative path absolute."""
        return str(self.path.joinpath(path).resolve())

    def absolute_paths(self, paths: Iterable[str]) -> Set[str]:
        """Make directory-relative paths absolute."""
        return set(
            self.absolute_path(path)
            for path
            in paths)

    def grep(
            self,
            args: Iterable,
            target: Optional[str] = None) -> AwaitableGenerator:
        return AwaitableGenerator(
            self._grep(args, target),
            collector=async_set,
            predicate=self._include_file)

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
        return str(pathlib.Path(path).relative_to(self.path))

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
        # Currently this generation is a little pointless, but is here in
        # anticipation of https://github.com/envoyproxy/pytooling/issues/246
        # getting fixed.
        try:
            for path in await self.shell(self.parse_grep_args(args, target)):
                if path:
                    yield path
        except subprocess_exceptions.RunError as e:
            response = e.args[1]
            grep_fail = (
                (response.returncode == 1)
                and not response.stdout
                and not response.stderr)
            if not grep_fail:
                raise e

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
        if not self.changed:
            return await super().files
        # If the super `files` are going to be filtered fetch them first, and
        # only check `changed_files` if there are any matching. Otherwise do
        # the reverse - get the `changed_files` and bail if there are none.
        no_match = (
            ((self.path_matcher or self.exclude_matcher)
             and not await super().files)
            or not await self.changed_files)
        return (
            set()
            if no_match
            else (
                await super().files
                & await self.changed_files))

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
