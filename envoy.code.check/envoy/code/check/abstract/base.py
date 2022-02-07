
from typing import Dict, List, Set

import abstracts

from aio.core.directory import ADirectory
from aio.core.functional import async_property


class ACodeCheck(metaclass=abstracts.Abstraction):

    def __init__(self, directory: ADirectory, fix: bool = False) -> None:
        self.directory = directory
        self._fix = fix

    @async_property(cache=True)
    async def absolute_paths(self) -> Set[str]:
        return self.directory.absolute_paths(await self.files)

    @async_property
    @abstracts.interfacemethod
    async def checker_files(self) -> Set[str]:
        raise NotImplementedError

    @async_property(cache=True)
    async def files(self) -> Set[str]:
        files = await self.directory.files
        return (
            files & await self.checker_files
            if files
            else files)

    @property
    def fix(self) -> bool:
        return self._fix

    @async_property
    @abstracts.interfacemethod
    async def problem_files(self) -> Dict[str, List[str]]:
        raise NotImplementedError
