
import asyncio
import re
from functools import cached_property, partial
from typing import (
    Callable, Iterable, Iterator,
    Pattern, Set, Tuple)

import abstracts

from aio.core.dev import debug
from aio.core.functional import async_property
from aio.core.directory.utils import directory_context  # type:ignore

from envoy.base import utils
from envoy.code.check import abstract, typing


NOGLINT_RE = (
    r"[\w/]*\.patch$",
    r"^test/[\w/]*_corpus/[\w/]*",
    r"^tools/[\w/]*_corpus/[\w/]*",
    r"[\w/]*password_protected_password.txt$")


@debug.logging(
    log=__name__,
    show_cpu=True)
def _have_newlines(path: str, paths: Iterable[str]) -> Set[str]:
    with directory_context(path):
        return set(
            target
            for target
            in paths
            if (utils.last_n_bytes_of(target)
                != b'\n'))


class AGlintCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def have_newlines(cls, path: str, *paths: str) -> Set[str]:
        return _have_newlines(path, paths)

    @classmethod
    def filter_files(
            cls, files: Set[str],
            match: Callable) -> Set[str]:
        return set(
            path
            for path
            in files
            if not match(path))

    @async_property
    async def checker_files(self) -> Set[str]:
        return self.filter_files(
            await self.directory.files,
            self.noglint_re.match)

    @async_property
    async def files_with_mixed_tabs(self) -> Set[str]:
        return await self.directory.grep(
            ["-lP", r"^ "],
            target=await self.files_with_preceeding_tabs)

    @async_property
    async def files_with_preceeding_tabs(self) -> Set[str]:
        return await self.directory.grep(
            ["-lP", r"^\t"],
            target=await self.files)

    @async_property
    async def files_with_no_newline(self) -> Set[str]:
        batched = self.execute_in_batches(
            partial(self.have_newlines, self.directory.path),
            *await self.files)
        no_newline = set()
        async for batch in batched:
            no_newline |= batch
        return no_newline

    @async_property
    async def files_with_trailing_whitespace(self) -> Set[str]:
        return await self.directory.grep(
            ["-lE", "[[:blank:]]$"],
            target=await self.files)

    @cached_property
    def noglint_re(self) -> Pattern[str]:
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
            problems: Tuple[
                Set[str], Set[str], Set[str]]) -> typing.ProblemDict:
        return {
            path: list(self._check_path(path, *problems))
            for path
            in (problems[0] | problems[1] | problems[2])}

    def _check_path(
            self,
            path: str,
            no_newline: Set[str],
            mixed_tabs: Set[str],
            trailing_whitespace: Set[str]) -> Iterator[str]:
        if path in no_newline:
            yield f"Missing final newline: {path}"
        if path in mixed_tabs:
            yield f"Mixed preceeding tabs and whitespace: {path}"
        if path in trailing_whitespace:
            yield f"Trailing whitespace: {path}"
