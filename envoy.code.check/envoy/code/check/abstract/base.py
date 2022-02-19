
import asyncio
from concurrent import futures
from typing import Dict, List, Optional, Set

import abstracts

from aio.core import event
from aio.core.directory import ADirectory
from aio.core.functional import async_property


@abstracts.implementer(event.IReactive)
class ACodeCheck(event.AReactive, metaclass=abstracts.Abstraction):

    def __init__(
            self,
            directory: ADirectory,
            fix: bool = False,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            pool: Optional[futures.Executor] = None) -> None:
        self.directory = directory
        self._fix = fix
        self._loop = loop
        self._pool = pool

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
