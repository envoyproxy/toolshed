
import pathlib
from typing import AsyncIterator, Awaitable, Set

import yapf  # type:ignore

import abstracts

from aio.core import tasks
from aio.core.functional import async_property, AwaitableGenerator

from envoy.code.check import abstract, typing


YAPF_CONFIG = '.style.yapf'


class AYapfCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def yapf_files(
            cls,
            directory_path: str,
            py_files: str) -> Set[str]:
        return set(
            yapf.file_resources.GetCommandLineFiles(
                py_files,
                recursive=False,
                exclude=yapf.file_resources.GetExcludePatternsForDir(
                    directory_path)))

    @classmethod
    def yapf_format(
            cls,
            rel_path: str,
            abs_path: str,
            config_path: str,
            fix: bool = False) -> "typing.YapfProblemTuple":
        return (
            cls._yapf_result(
                rel_path,
                yapf.yapf_api.FormatFile(
                    abs_path,
                    style_config=config_path,
                    in_place=fix,
                    print_diff=not fix)))

    @classmethod
    def _yapf_result(
            cls,
            path: str,
            yapf_result: "typing.YapfResultTuple") -> (
                "typing.YapfProblemTuple"):
        reformatted, encoding, changed = yapf_result
        return (
            (path,
             ([]
              if not changed and not reformatted
              else (
                  [f"Issues found (fixed): {path}"]
                  if changed and not reformatted
                  else [f"Issues found: {path}\n{reformatted}"]))))

    @async_property
    async def checker_files(self) -> Set[str]:
        # todo: add grep for py shebang files
        return self.directory.relative_paths(await self.yapf_file_resources)

    @property
    def config_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(YAPF_CONFIG)

    @async_property(cache=True)
    async def problem_files(self) -> "typing.ProblemDict":
        return (
            dict(await AwaitableGenerator(self._problem_files))
            if await self.files
            else {})

    @async_property(cache=True)
    async def py_files(self) -> Set[str]:
        return await self.directory.make_paths_absolute(
            tuple(
                path
                for path
                in await self.directory.files
                if path.endswith(".py")))

    @async_property
    async def yapf_file_resources(self) -> Set[str]:
        return (
            await self.execute(
                self.yapf_files,
                str(self.directory.path),
                await self.py_files)
            if await self.py_files
            else set())

    @async_property
    async def _problem_files(self) -> AsyncIterator["typing.YapfProblemTuple"]:
        if not await self.files:
            return
        async for path, problem in tasks.concurrent(self._yapf_checks, limit=4):
            if problem:
                yield path, problem

    @async_property
    async def _yapf_checks(self) -> AsyncIterator[Awaitable]:
        for path in await self.absolute_paths:
            yield self.execute(
                self.yapf_format,
                str(self.directory.relative_path(path)),
                path,
                str(self.config_path),
                self.fix)
