
import re
import shutil
from functools import cached_property
from typing import Dict, List, Set, Tuple

import abstracts

from aio.core.functional import async_property

from envoy.code.check import abstract, exceptions


SHEBANG_RE = (
    r"^#!/bin/bash",
    r"^#!/bin/sh",
    r"^#!/usr/bin/env bash",
    r"^#!/usr/bin/env sh")
SHELLCHECK_MATCH_RE = (
    r"[\w/]*\.sh$", )
SHELLCHECK_NOMATCH_RE = (
    r"[\w/]*\.rst$",
    r"[\w/]*\.md$",
    r"[\w/]*\.genrule_cmd$")


class AShellcheckCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):

    @async_property
    async def checker_files(self) -> Set[str]:
        return (
            await self.sh_files
            | await self.shebang_files)

    @cached_property
    def path_match_exclude_re(self):
        return re.compile("|".join(SHELLCHECK_NOMATCH_RE))

    @cached_property
    def path_match_re(self):
        return re.compile("|".join(SHELLCHECK_MATCH_RE))

    @async_property(cache=True)
    async def problem_files(self) -> Dict[str, List[str]]:
        return (
            dict(await self._problem_files)
            if await self.files
            else {})

    @async_property
    async def sh_files(self) -> Set[str]:
        return set(
            path
            for path
            in await self.directory.files
            if (self.path_match_re.match(path)
                and not self.path_match_exclude_re.match(path)))

    @async_property
    async def shebang_files(self) -> Set[str]:
        """Files that contain shebang lines, excluding actual .sh files and
        others, eg md/rst, that may have such lines for other reasons."""
        return set(
            path
            for path
            in await self.directory.grep(
                ["-lE",
                 self.shebang_re_expr,
                 *await self._possible_shebang_files]))

    @property
    def shebang_re_expr(self) -> str:
        return "|".join(SHEBANG_RE)

    @cached_property
    def shellcheck_command(self) -> str:
        command = shutil.which("shellcheck")
        if command:
            return command
        raise exceptions.ShellcheckError(
            "Unable to find shellcheck command")

    @async_property
    async def _problem_files(self) -> List[Tuple[str, List[str]]]:
        return await self.directory.shell.parallel(
            ([self.shellcheck_command, "-x", path]
             for path
             in await self.files),
            predicate=lambda result: result.returncode,
            result=lambda response: (
                response.args[-1],
                [f"Issues found: {response.args[-1]}\n"
                 f"{response.stdout}"]))

    @async_property
    async def _possible_shebang_files(self) -> Set[str]:
        return set(
            path
            for path
            in await self.directory.files
            if (not self.path_match_re.match(path)
                and not self.path_match_exclude_re.match(path)))
