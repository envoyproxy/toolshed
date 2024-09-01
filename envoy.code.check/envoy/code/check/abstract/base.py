
import asyncio
import pathlib
from concurrent import futures
from functools import cached_property
from typing import Dict, List, Optional, Set

import yaml

import abstracts

from aio.core import event
from aio.core.directory import ADirectory
from aio.core.functional import async_property

from envoy.base import utils
from envoy.code.check import interface


@abstracts.implementer(event.IExecutive)
class ACodeCheck(event.AExecutive, metaclass=abstracts.Abstraction):

    def __init__(
            self,
            directory: ADirectory,
            fix: bool = False,
            binaries: Optional[Dict[str, str]] = None,
            config: Optional[pathlib.Path] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            pool: Optional[futures.Executor] = None) -> None:
        self.directory = directory
        self._fix = fix
        self._loop = loop
        self._pool = pool
        self._binaries = binaries
        self._config = config

    @property
    def binaries(self):
        return self._binaries

    @cached_property
    def config(self):
        return (
            yaml.safe_load(self._config.read_text())
            if self._config
            else {})


@abstracts.implementer(interface.IFileCodeCheck)
class AFileCodeCheck(ACodeCheck, metaclass=abstracts.Abstraction):

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
