
import os
import pathlib
from functools import partial
from typing import AsyncIterator, Iterable, Iterator, Optional, Set, Tuple

import yapf  # type:ignore

import abstracts

from aio.core.dev import debug
from aio.core.functional import (
    async_property,
    AwaitableGenerator,
    directory_context)

from envoy.code.check import abstract, typing


YAPF_CONFIG = '.style.yapf'


class YapfFormatCheck:
    """Wraps `yapf_api.FormatFile` to run it on multiple paths in a subproc."""

    def __init__(
            self,
            root_path: str,
            config_path: str,
            fix: bool,
            *args) -> None:
        self.root_path = root_path
        self.config_path = config_path
        self.fix = fix
        self.args = args

    @property
    def check_results(self) -> Iterator["typing.YapfProblemTuple"]:
        for path in self.args:
            result = self.handle_result(
                path,
                yapf.yapf_api.FormatFile(
                    os.path.join(self.root_path, path),
                    style_config=self.config_path,
                    in_place=self.fix,
                    print_diff=not self.fix))
            if result:
                yield result

    def handle_result(
            self,
            path: str,
            yapf_result: "typing.YapfResultTuple") -> Optional[
                "typing.YapfProblemTuple"]:
        reformatted, encoding, changed = yapf_result
        if not (changed or reformatted):
            return None
        return (
            path,
            ([f"Issues found (fixed): {path}"]
             if changed and not reformatted
             else [f"Issues found: {path}\n{reformatted}"]))

    @debug.logging(
        log=__name__,
        show_cpu=True)
    def run_checks(self) -> Tuple["typing.YapfProblemTuple", ...]:
        return tuple(self.check_results)


@debug.logging(
    log=__name__,
    show_cpu=True)
def _yapf_files(directory_path: str, py_files: Iterable[str]) -> Set[str]:
    with directory_context(directory_path):
        return set(
            yapf.file_resources.GetCommandLineFiles(
                py_files,
                recursive=False,
                exclude=yapf.file_resources.GetExcludePatternsForDir(
                    directory_path)))


class AYapfCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def yapf_files(
            cls,
            directory_path: str,
            *py_files: str) -> Set[str]:
        return _yapf_files(directory_path, py_files)

    @classmethod
    def yapf_format(
            cls,
            root_path: str,
            config_path: str,
            fix: bool,
            *args) -> "typing.YapfProblemTuple":
        return YapfFormatCheck(root_path, config_path, fix, *args).run_checks()

    @async_property
    async def checker_files(self) -> Set[str]:
        # todo: add grep for py shebang files
        py_files = await self.py_files
        if not py_files:
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
        return self.directory.path.joinpath(YAPF_CONFIG)

    @async_property(cache=True)
    async def problem_files(self) -> "typing.ProblemDict":
        return dict(await AwaitableGenerator(self._problem_files))

    @async_property(cache=True)
    async def py_files(self) -> Set[str]:
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
