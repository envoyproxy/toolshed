
import os
import pathlib
from functools import partial
from typing import AsyncIterator, Iterable, Iterator, Optional, Set, Tuple

import yapf  # type:ignore

import abstracts

from aio.core import directory
from aio.core.dev import debug
from aio.core.functional import (
    async_property,
    AwaitableGenerator)
from aio.run import checker

from envoy.code.check import abstract, typing


YAPF_CONFIG = '.style.yapf'


@abstracts.implementer(directory.IDirectoryContext)
class YapfFormatCheck(directory.ADirectoryContext):
    """Wraps `yapf_api.FormatFile` to run it on multiple paths in a subproc."""

    def __init__(
            self,
            path: str,
            config_path: str,
            fix: bool,
            *args) -> None:
        directory.ADirectoryContext.__init__(self, path)
        self.config_path = config_path
        self.fix = fix
        self.args = args

    @property
    def check_results(self) -> Iterator["typing.YapfProblemTuple"]:
        """Iterate Yapf check results."""
        for path in self.args:
            try:
                result = self.handle_result(
                    path,
                    yapf.yapf_api.FormatFile(
                        os.path.join(self.path, path),
                        style_config=self.config_path,
                        in_place=self.fix,
                        print_diff=not self.fix))
            except yapf.errors.YapfError as e:
                yield path, checker.Problems(
                    errors=[f"Yaml check failed: {path}\n{e}"])
            else:
                if result:
                    yield result

    def handle_result(
            self,
            path: str,
            yapf_result: "typing.YapfResultTuple") -> Optional[
                "typing.YapfProblemTuple"]:
        """Handle a Yapf check result converting to a path and error list."""
        reformatted, encoding, changed = yapf_result
        if not (changed or reformatted):
            return None
        return (
            path,
            (checker.Problems(errors=[f"Issues found (fixed): {path}"])
             if changed and not reformatted
             else checker.Problems(
                     errors=[f"Issues found: {path}\n{reformatted}"])))

    @debug.logging(
        log=__name__,
        show_cpu=True)
    def run_checks(self) -> Tuple["typing.YapfProblemTuple", ...]:
        """Run Yapf checks."""
        return tuple(self.check_results)


@abstracts.implementer(directory.IDirectoryContext)
class YapfFiles(directory.ADirectoryContext):

    @debug.logging(
        log=__name__,
        show_cpu=True)
    def filter_files(self, py_files: Iterable[str]) -> Set[str]:
        with self.in_directory:
            return set(
                yapf.file_resources.GetCommandLineFiles(
                    py_files,
                    recursive=False,
                    exclude=yapf.file_resources.GetExcludePatternsForDir(
                        self.path)))


class AYapfCheck(abstract.AFileCodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def yapf_files(
            cls,
            directory_path: str,
            *py_files: str) -> Set[str]:
        """Yapf file discovery for a given file list."""
        return YapfFiles(directory_path).filter_files(py_files)

    @classmethod
    def yapf_format(
            cls,
            root_path: str,
            config_path: str,
            fix: bool,
            *args) -> "typing.YapfProblemTuple":
        """Run Yapf checks on provided file list."""
        return YapfFormatCheck(root_path, config_path, fix, *args).run_checks()

    @async_property
    async def checker_files(self) -> Set[str]:
        # todo: add grep for py shebang files
        if not (py_files := await self.py_files):
            return set()
        resources = set()
        batches = self.execute_in_batches(
            partial(
                self.yapf_files,
                str(self.directory.path)),
            *py_files)
        async for batch in batches:
            resources |= batch
        return resources

    @property
    def config_path(self) -> pathlib.Path:
        """Path to the Yapf config file."""
        return self.directory.path.joinpath(YAPF_CONFIG)

    @async_property(cache=True)
    async def problem_files(self) -> "typing.ProblemDict":
        return dict(await AwaitableGenerator(self._problem_files))

    @async_property(cache=True)
    async def py_files(self) -> Set[str]:
        """Files with a `.py` suffix."""
        return set(
            path
            for path
            in await self.directory.files
            if path.endswith(".py"))

    @async_property
    async def _problem_files(self) -> AsyncIterator["typing.YapfProblemTuple"]:
        if not await self.files:
            return
        batches = self.execute_in_batches(
            partial(
                self.yapf_format,
                str(self.directory.path),
                str(self.config_path),
                self.fix),
            *await self.files)

        async for batch in batches:
            for path, problem in batch:
                yield path, problem
