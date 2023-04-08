
import pathlib
import re
import shutil
import subprocess
from functools import cached_property, partial
from typing import (
    Optional, Pattern)

import abstracts

from aio.core.functional import async_property
from aio.core import subprocess as _subprocess
from aio.run import checker

from envoy.code.check import abstract, interface, typing

NOGOFMT_RE = ()


class GofmtError(Exception):
    pass


@abstracts.implementer(_subprocess.ISubprocessHandler)
class Gofmt(_subprocess.ASubprocessHandler):
    """Wraps `Gofmt` to run it on multiple paths in a subproc."""

    def handle(
            self,
            response: subprocess.CompletedProcess) -> typing.ProblemDict:
        """Handle response for `gofmt`."""
        if response.args[1] == "-d":
            return self.handle_diff(response)
        return self.handle_problems(response)

    def handle_diff(
            self,
            response: subprocess.CompletedProcess) -> typing.ProblemDict:
        """Handle response for `gofmt -d`.

        As `gofmt` is called with multiple files, we need to parse the
        diff line-by-line to match the diff content with the file that has
        generated it.

        Returns the parsed or provided `filename`. If this is empty, or
        doesnt match the files that we called `gofmt` with then something has
        gone wrong.
        """

        result: typing.ProblemDict = dict()
        if not response.stdout:
            return result
        files = response.args[2:]
        filename = ""
        for line in response.stdout.splitlines():
            filename = self._diff_line(filename, result, line)
            # If we didnt get a matching file back, then diff parsing failed.
            if not filename:
                raise GofmtError(f"Unable to parse: {response}")
            if filename not in files:
                raise GofmtError(
                    "Unable to parse filename "
                    f"({filename}): {response}")
        return result

    def handle_error(
            self,
            response: subprocess.CompletedProcess) -> typing.ProblemDict:
        """Handle error response for `gofmt`."""
        raise GofmtError(response)

    def handle_problems(
            self,
            response: subprocess.CompletedProcess) -> typing.ProblemDict:
        """Handle response for `gofmt -l/w`."""
        return dict(
            reformat=checker.Problems(
                errors=response.stdout.splitlines()))

    def _diff_line(
            self,
            filename: str,
            result: typing.ProblemDict,
            line: str) -> str:
        if not line.startswith("diff -u"):
            # Append diff line
            result[filename].errors[0] += f"{line}\n"
            return filename
        # Start of a diff
        filename = line.split()[-1]
        result[filename] = result.get(
            filename,
            checker.Problems(
                errors=[
                    "Requires reformatting: "
                    f"{filename}\n{line}\n"]))
        return filename


@abstracts.implementer(interface.IGofmtCheck)
class AGofmtCheck(abstract.AFileCodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def filter_files(
            cls,
            files: set[str],
            exclude: Optional[Pattern[str]]) -> set[str]:
        """Filter files for `gofmt` checking."""
        return set(
            path
            for path
            in files
            if (not exclude
                or not exclude.match(path)))

    @classmethod
    def gofmt(self, path: str, *args) -> typing.ProblemDict:
        """Run gofmt on files."""
        return Gofmt(path)(*args)

    @async_property
    async def checker_files(self) -> set[str]:
        return self.filter_files(
            await self.go_files,
            self.nogofmt_re)

    @async_property(cache=True)
    async def fixable_files(self) -> set[str]:
        """Files that can be fixed by Gofmt."""
        jobs = self.execute_in_batches(
            self.gofmt_problems,
            *await self.files)
        problem_files = set()
        async for result in jobs:
            problem_files |= set(result["reformat"].errors)
        return problem_files

    @async_property
    async def fixed_files(self) -> "typing.ProblemDict":
        """Files that have been fixed by Gofmt."""
        # Gofmt doesnt give any feedback about changes - so we have
        # to first get the set of fixable files, then run the fixes
        # and then return the original files.
        jobs = self.execute_in_batches(
            self.gofmt_fix,
            *await self.fixable_files)
        async for result in jobs:
            pass
        return {
            f: checker.Problems(errors=[f"Reformatted: {f}"])
            for f
            in await self.fixable_files}

    @async_property(cache=True)
    async def go_files(self) -> set[str]:
        """Files with a `.go` suffix."""
        return set(
            path
            for path
            in await self.directory.files
            if path.endswith(".go"))

    @cached_property
    def gofmt_command(self) -> str | pathlib.Path:
        """Gofmt command, should be available in the running system."""
        if "gofmt" in self.binaries:
            return pathlib.Path(self.binaries["gofmt"]).absolute()
        if command := shutil.which("gofmt"):
            return command
        raise _subprocess.exceptions.OSCommandError(
            "Unable to find gofmt command")

    @cached_property
    def gofmt_diff(self) -> partial:
        """Partial with gofmt command and diff arg."""
        return self._gofmt("-d")

    @cached_property
    def gofmt_fix(self) -> partial:
        """Partial with gofmt command and write arg."""
        return self._gofmt("-w")

    @cached_property
    def gofmt_problems(self) -> partial:
        """Partial with gofmt command and list arg."""
        return self._gofmt("-l")

    @cached_property
    def nogofmt_re(self) -> Optional[Pattern[str]]:
        """Regex for matching files that should not be checked."""
        # TODO(phlax): merge e.c.c config
        if not NOGOFMT_RE:
            return None
        return re.compile(r"|".join(NOGOFMT_RE))

    @async_property(cache=True)
    async def problem_files(self) -> "typing.ProblemDict":
        """Problematic Go files detected by Gofmt."""
        errors: typing.ProblemDict = dict()
        if self.fix:
            return await self.fixed_files
        jobs = self.execute_in_batches(
            self.gofmt_diff,
            *await self.files)
        async for result in jobs:
            if result:
                errors.update(result)
        return errors

    def _gofmt(self, *args: str) -> partial:
        """Partial with gofmt command and args."""
        return partial(
            self.gofmt,
            self.directory.path,
            self.gofmt_command,
            *args)
