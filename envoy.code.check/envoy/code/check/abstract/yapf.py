
import pathlib
from typing import Dict, List, Set, Tuple

import yapf  # type:ignore

import abstracts

from aio.core.functional import async_list, async_map, async_property

from envoy.code.check import abstract


YAPF_CONFIG = '.style.yapf'


class AYapfCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):

    @async_property
    async def checker_files(self) -> Set[str]:
        # todo: add grep for py shebang files
        return self.directory.relative_paths(await self.yapf_file_resources)

    @async_property(cache=True)
    async def problem_files(self) -> Dict[str, List[str]]:
        return (
            dict(await self._problem_files)
            if await self.files
            else {})

    @async_property
    async def py_files(self) -> Set[str]:
        return self.directory.absolute_paths(
            path
            for path
            in await self.directory.files
            if path.endswith(".py"))

    @property
    def yapf_config_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(YAPF_CONFIG)

    @async_property
    async def yapf_file_resources(self) -> List[str]:
        return (
            yapf.file_resources.GetCommandLineFiles(
                await self.py_files,
                recursive=False,
                exclude=yapf.file_resources.GetExcludePatternsForDir(
                    str(self.directory.path)))
            if await self.py_files
            else [])

    @async_property
    async def _problem_files(self):
        return await async_list(
            async_map(
                self.yapf_format,
                await self.absolute_paths,
                fork=True),
            predicate=lambda result: result[1][2],
            result=self._handle_problem)

    def yapf_format(self, python_file: str) -> tuple:
        return (
            self.directory.relative_path(python_file),
            yapf.yapf_api.FormatFile(
                python_file,
                style_config=str(self.yapf_config_path),
                in_place=self.fix,
                print_diff=not self.fix))

    def _handle_problem(self, problem) -> Tuple[str, List[str]]:
        path, result = problem
        reformatted, encoding, changed = result
        return (
            (path,
             ([f"Issues found (fixed): {path}"]
              if changed and not reformatted
              else [f"Issues found: {path}\n{reformatted}"])))
