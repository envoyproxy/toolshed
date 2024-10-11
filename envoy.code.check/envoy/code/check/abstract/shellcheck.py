
import os
import pathlib
import re
import shutil
import subprocess
from functools import cached_property, partial
from typing import Iterator, Pattern, TypedDict

import abstracts

from aio.core import subprocess as _subprocess
from aio.core.functional import async_property
from aio.run import checker

from envoy.code.check import abstract, interface, typing


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


class ShellcheckErrorDict(TypedDict):
    lines: list[str]
    line_numbers: list[int]


@abstracts.implementer(_subprocess.ISubprocessHandler)
class Shellcheck(_subprocess.ASubprocessHandler):

    @cached_property
    def error_line_re(self) -> Pattern[str]:
        """Regex for matching a shellcheck error line.

        This demarcates the beginning of a specific error for a file.
        """
        return re.compile(SHELLCHECK_ERROR_LINE_RE)

    def handle(
            self,
            response: subprocess.CompletedProcess) -> typing.ProblemDict:
        return {}

    def handle_error(
            self,
            response: subprocess.CompletedProcess) -> typing.ProblemDict:
        """Turn the response from a call to shellcheck (for multiple files)
        into an `typing.ProblemDict`."""
        return self._render_errors(self._shellcheck_errors(response))

    def parse_error_line(self, line: str) -> tuple[str, int | None]:
        """Parse `filename`, `line_number` from a shellcheck error line."""
        matched = self.error_line_re.search(line)
        return (
            (matched.groups()[0],
             int(matched.groups()[1]))
            if matched
            else ("", None))

    def _render_errors(
            self,
            errors: Iterator[
                tuple[
                    str,
                    ShellcheckErrorDict]]) -> typing.ProblemDict:
        return {
            k: checker.Problems(errors=self._render_file_errors(k, v))
            for k, v
            in errors}

    def _render_file_errors(
            self,
            path: str,
            errors: ShellcheckErrorDict) -> list[str]:
        # This does v basic en pluralization
        line_numbers = ", ".join(str(n) for n in errors["line_numbers"])
        lines = (
            "lines"
            if len(errors["line_numbers"]) > 1
            else "line")
        return [
            "\n".join([
                f"{path} ({lines}: {line_numbers})",
                *errors["lines"]])]

    def _shellcheck_error_info(
            self,
            filename: str | None = None) -> tuple[
                str | None, ShellcheckErrorDict]:
        return (
            filename,
            dict(line_numbers=[], lines=[]))

    def _shellcheck_errors(
            self,
            response: subprocess.CompletedProcess) -> Iterator[
                tuple[str, ShellcheckErrorDict]]:
        filename, info = self._shellcheck_error_info()
        for line in response.stdout.split("\n"):
            _filename, line_number = self.parse_error_line(line)
            if _filename and line_number:
                # matches as error line - may/not be a new error for this file
                if filename and (_filename != filename):
                    # filename boundary - yield, and reset
                    yield filename, info
                    filename, info = self._shellcheck_error_info(_filename)
                # add line number to error line_numbers
                info["line_numbers"].append(line_number)
                filename = _filename
            if filename is None:
                # preceeding whitespace
                continue
            info["lines"].append(line)
        if filename:
            # flush the buffer
            yield filename, info


@abstracts.implementer(interface.IShellcheckCheck)
class AShellcheckCheck(
        abstract.AFileCodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def run_shellcheck(
            self,
            path: str | os.PathLike,
            *args) -> typing.ProblemDict:
        """Run shellcheck on files."""
        return Shellcheck(path)(*args)

    @async_property
    async def checker_files(self) -> set[str]:
        return (
            await self.sh_files
            | await self.shebang_files)

    @cached_property
    def path_match_exclude_re(self) -> Pattern[str]:
        """Regex to match files not to check."""
        return re.compile("|".join(SHELLCHECK_NOMATCH_RE))

    @cached_property
    def path_match_re(self) -> Pattern[str]:
        """Regex to match files to check."""
        return re.compile("|".join(SHELLCHECK_MATCH_RE))

    @async_property(cache=True)
    async def problem_files(self) -> typing.ProblemDict:
        """Discovered shellcheck errors."""
        if not await self.files:
            return {}
        errors: typing.ProblemDict = {}
        jobs = self.execute_in_batches(
            self.shellcheck_executable,
            *await self.files)
        async for result in jobs:
            errors.update(result)
        return errors

    @async_property
    async def sh_files(self) -> set[str]:
        """Files with a `.sh` suffix, but that are not excluded."""
        return set(
            path
            for path
            in await self.directory.files
            if (self.path_match_re.match(path)
                and not self.path_match_exclude_re.match(path)))

    @async_property
    async def shebang_files(self) -> set[str]:
        """Files that contain shebang lines, excluding actual .sh files and
        others, eg md/rst, that may have such lines for other reasons."""
        return await self.directory.grep(
            ["-lE", self.shebang_re_expr],
            target=await self._possible_shebang_files)

    @property
    def shebang_re_expr(self) -> str:
        """Regex for matching shebang lines _in_ a file."""
        return "|".join(SHEBANG_RE)

    @cached_property
    def shellcheck_command(self) -> str | pathlib.Path:
        """Shellcheck command, should be available in the running system."""
        if "shellcheck" in self.binaries:
            return pathlib.Path(self.binaries["shellcheck"]).absolute()
        if command := shutil.which("shellcheck"):
            return command
        raise _subprocess.exceptions.OSCommandError(
            "Unable to find shellcheck command")

    @cached_property
    def shellcheck_executable(self) -> partial:
        """Partial with shellcheck command and args."""
        return partial(
            self.run_shellcheck,
            self.directory.path,
            self.shellcheck_command,
            "-x")

    @async_property
    async def _possible_shebang_files(self) -> set[str]:
        return set(
            path
            for path
            in await self.directory.files
            if (not self.path_match_re.match(path)
                and not self.path_match_exclude_re.match(path)))
