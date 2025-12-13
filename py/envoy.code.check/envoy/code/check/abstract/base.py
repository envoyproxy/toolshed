
import asyncio
from concurrent import futures

import abstracts

from aio.core import event
from aio.core.directory import ADirectory
from aio.core.functional import async_property

from envoy.base import utils
from envoy.code.check import interface, typing


@abstracts.implementer(event.IExecutive)
class ACodeCheck(event.AExecutive, metaclass=abstracts.Abstraction):

    def __init__(
            self,
            directory: ADirectory,
            fix: bool = False,
            binaries: dict[str, str] | None = None,
            config: typing.YAMLConfigDict | None = None,
            loop: asyncio.AbstractEventLoop | None = None,
            pool: futures.Executor | None = None) -> None:
        self.directory = directory
        self.config = config
        self._fix = fix
        self._loop = loop
        self._pool = pool
        self._binaries = binaries

    @property
    def binaries(self):
        return self._binaries


@abstracts.implementer(interface.IFileCodeCheck)
class AFileCodeCheck(ACodeCheck, metaclass=abstracts.Abstraction):

    @async_property
    @abstracts.interfacemethod
    async def checker_files(self) -> set[str]:
        raise NotImplementedError

    @async_property(cache=True)
    async def files(self) -> set[str]:
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
    async def problem_files(self) -> dict[str, list[str]]:
        """Discovered files with flake8 errors."""
        raise NotImplementedError


@abstracts.implementer(interface.IProjectCodeCheck)
class AProjectCodeCheck(ACodeCheck,  metaclass=abstracts.Abstraction):

    def __init__(
            self,
            project: utils.interface.IProject,
            *args,
            **kwargs) -> None:
        self.project = project
        super().__init__(project.directory, *args, **kwargs)
