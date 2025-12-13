
import asyncio
import pathlib
import re
from functools import cached_property, partial
from typing import (
    Callable, Iterable, Iterator, Pattern)

import abstracts

from aio.core.dev import debug
from aio.core import directory
from aio.core.functional import async_property
from aio.run import checker

from envoy.base import utils
from envoy.code.check import abstract, interface, typing


NOGLINT_RE = (
    r"[\w\W/-]*\.go$",
    r"[\w\W/-]*\.patch$",
    r"^test/[\w/]*_corpus/[\w/]*",
    r"^tools/[\w/]*_corpus/[\w/]*",
    r"[\w/]*password_protected_password.txt$")


@abstracts.implementer(directory.IDirectoryContext)
class NewlineChecker(directory.ADirectoryContext):

    @debug.logging(
        log=__name__,
        show_cpu=True)
    def no_newlines(
            self,
            paths: Iterable[str | pathlib.Path]) -> set[str | pathlib.Path]:
        """Check files for final newline."""
        with self.in_directory:
            return set(
                target
                for target
                in paths
                if not self._has_newline(target))

    def _has_newline(self, target: str | pathlib.Path) -> bool:
        return (
            utils.last_n_bytes_of(target)
            == b'\n')


@abstracts.implementer(interface.IGlintCheck)
class AGlintCheck(abstract.AFileCodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def no_newlines(
            cls,
            path: str | pathlib.Path,
            *paths: str | pathlib.Path) -> set[str]:
        """Check files for final newline."""
        return NewlineChecker(path).no_newlines(paths)

    @classmethod
    def filter_files(
            cls, files: set[str],
            match: Callable) -> set[str]:
        """Filter files for `glint` checking."""
        return set(
            path
            for path
            in files
            if not match(path))

    @async_property
    async def checker_files(self) -> set[str]:
        return self.filter_files(
            await self.directory.files,
            self.noglint_re.match)

    @async_property
    async def files_with_mixed_tabs(self) -> set[str]:
        """Files with mixed preceeding tabs and spaces."""
        return await self.directory.grep(
            ["-lP", r"^ "],
            target=await self.files_with_preceeding_tabs)

    @async_property
    async def files_with_preceeding_tabs(self) -> set[str]:
        """Files with preceeding tabs."""
        return await self.directory.grep(
            ["-lP", r"^\t"],
            target=await self.files)

    @async_property
    async def files_with_no_newline(self) -> set[str]:
        """Files with no final newline."""
        batched = self.execute_in_batches(
            partial(self.no_newlines, self.directory.path),
            *await self.files)
        no_newline = set()
        async for batch in batched:
            no_newline |= batch
        return no_newline

    @async_property
    async def files_with_trailing_whitespace(self) -> set[str]:
        """Files with trailing whitespace."""
        return await self.directory.grep(
            ["-lE", "[[:blank:]]$"],
            target=await self.files)

    @cached_property
    def noglint_re(self) -> Pattern[str]:
        """Regex for matching files that should not be checked."""
        return re.compile(r"|".join(NOGLINT_RE))

    @async_property(cache=True)
    async def problem_files(self) -> typing.ProblemDict:
        return (
            await self._check_problems(
                await asyncio.gather(
                    self.files_with_no_newline,
                    self.files_with_mixed_tabs,
                    self.files_with_trailing_whitespace))
            if await self.files
            else {})

    async def _check_problems(
            self,
            problems: tuple[
                set[str], set[str], set[str]]) -> typing.ProblemDict:
        return {
            path: checker.Problems(
                errors=list(self._check_path(path, *problems)))
            for path
            in (problems[0] | problems[1] | problems[2])}

    def _check_path(
            self,
            path: str,
            no_newline: set[str],
            mixed_tabs: set[str],
            trailing_whitespace: set[str]) -> Iterator[str]:
        if path in no_newline:
            yield f"Missing final newline: {path}"
        if path in mixed_tabs:
            yield f"Mixed preceeding tabs and whitespace: {path}"
        if path in trailing_whitespace:
            yield f"Trailing whitespace: {path}"
