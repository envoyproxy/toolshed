
import logging
import os
import re
import shutil
import subprocess
from functools import cached_property, partial
from typing import AsyncIterator, Dict, List, Set, Tuple

import psutil

import abstracts

from aio.core import tasks
from aio.core.dev import debug
from aio.core.functional import async_property, batch_jobs

from envoy.code.check import abstract, exceptions


logger = logging.getLogger(__name__)

SHELLCHECK_ERROR_LINE_RE = r"In ([\w\-\_\./]+) line ([0-9]+):"
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
_ERROR_LINE_RE = re.compile(SHELLCHECK_ERROR_LINE_RE)

ErrorDict = Dict[str, List[str]]


class Shellcheck:

    def __init__(
            self,
            path: str,
            *args) -> None:
        self.path = path
        self.args = args

    def handle_errors(self, response: subprocess.CompletedProcess) -> ErrorDict:
        """Turn the response from a call to shellcheck (for multiple files)
        into an `ErrorDict`."""
        errors = {}
        if not response.returncode:
            return {}
        filename = None
        for line in response.stdout.split("\n"):
            _filename, line_number = self.parse_error_line(line)
            if _filename:
                filename = _filename
                errors[filename] = errors.get(filename, dict(line_numbers=[], lines=[]))
                errors[filename]["line_numbers"].append(line_number)
            if filename is None:
                continue
            errors[filename]["lines"].append(line)
        return self._render_errors(errors)

    def parse_error_line(self, line: str) -> Tuple[str, str]:
        """Parse `filename`, `line_number` from a shellcheck error line."""
        matched = _ERROR_LINE_RE.search(line)
        return (
            matched.groups()
            if matched
            else ("", ""))

    @debug.logging(
        log=__name__,
        show_cpu=True)
    def run_checks(self) -> ErrorDict:
        return self.handle_errors(
            subprocess.run(
                self.args,
                cwd=self.path,
                capture_output=True,
                encoding="utf-8"))

    def _render_errors(self, problems: Dict[str, Dict[str, List]]) -> ErrorDict:
        problem_files = []
        for k, v in problems.items():
            line_numbers = ", ".join(v["line_numbers"])
            lines = "lines" if len(v["line_numbers"]) > 1 else "line"
            problem_files.append((k, ["\n".join([f"{k} ({lines}: {line_numbers})", *v["lines"]])]))
        return problem_files


class AShellcheckCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def run_shellcheck(self, path: str, *args) -> ErrorDict:
        return Shellcheck(path, *args).run_checks()

    @async_property
    async def checker_files(self) -> Set[str]:
        return (
            await self.sh_files
            | await self.shebang_files)

    @async_property(cache=True)
    async def problem_files(self) -> ErrorDict:
        """Discovered shellcheck errors."""
        if not await self.files:
            return {}
        errors: ErrorDict = {}
        jobs =  self.execute_in_batches(
            self.shellcheck_executable,
            *await self.files)
        async for result in jobs:
            logger.debug(f"Received shellcheck result: {result}")
            errors.update(result)
        return errors

    @cached_property
    def shellcheck_executable(self):
        return partial(
            self.run_shellcheck,
            self.directory.path,
            self.shellcheck_command,
            "-x")

    @cached_property
    def path_match_exclude_re(self):
        return re.compile("|".join(SHELLCHECK_NOMATCH_RE))

    @cached_property
    def path_match_re(self):
        return re.compile("|".join(SHELLCHECK_MATCH_RE))

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
        return await self.directory.grep(
            ["-lE", self.shebang_re_expr],
            target=await self._possible_shebang_files)

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
    async def _possible_shebang_files(self) -> Set[str]:
        return set(
            path
            for path
            in await self.directory.files
            if (not self.path_match_re.match(path)
                and not self.path_match_exclude_re.match(path)))
