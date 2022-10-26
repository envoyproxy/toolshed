
import asyncio
import pathlib
from concurrent import futures
from typing import (
    AsyncIterator, Dict, Iterator, List, Optional, Set, Tuple, Type)

from packaging import version as _version

import abstracts

from aio.core import directory as _directory, event

from envoy.base import utils
from envoy.code.check import typing


class ICodeCheck(metaclass=abstracts.Interface):

    def __init__(
            self,
            directory: _directory.ADirectory,
            fix: bool = False,
            binaries: Optional[Dict[str, str]] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            pool: Optional[futures.Executor] = None) -> None:
        raise NotImplementedError


class IFileCodeCheck(ICodeCheck, metaclass=abstracts.Interface):

    @property  # type:ignore
    @abstracts.interfacemethod
    async def files(self) -> Set[str]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def problem_files(self) -> Dict[str, List[str]]:
        raise NotImplementedError


class IProjectCodeCheck(ICodeCheck, metaclass=abstracts.Interface):
    project: utils.interface.IProject

    def __init__(
            self,
            project: utils.interface.IProject,
            **kwargs) -> None:
        raise NotImplementedError


class IExtensionsCheck(metaclass=abstracts.Interface):

    def __init__(self, directory: _directory.ADirectory, **kwargs) -> None:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def all_fuzzed(self) -> bool:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def extensions_schema(self) -> "typing.ExtensionsSchemaDict":
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def fuzz_test_path(self) -> pathlib.Path:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def metadata(self) -> "typing.ExtensionsMetadataDict":
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def metadata_errors(self) -> Dict[str, Tuple[str, ...]]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def registration_errors(self) -> List[str]:
        raise NotImplementedError


class IFlake8Check(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IGlintCheck(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IShellcheckCheck(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IYapfCheck(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IRuntimeGuardsCheck(IProjectCodeCheck, metaclass=abstracts.Interface):

    @property  # type:ignore
    @abstracts.interfacemethod
    async def missing(self) -> Set[str]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def status(self) -> AsyncIterator[Tuple[str, Optional[bool]]]:
        raise NotImplementedError


class IChangelogChangesChecker(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def check_sections(
            self,
            version: _version.Version,
            sections: utils.typing.ChangelogChangeSectionsDict) -> (
                Tuple[str, ...]):
        raise NotImplementedError


class IChangelogStatus(metaclass=abstracts.Interface):
    pass


class IChangelogCheck(IProjectCodeCheck, metaclass=abstracts.Interface):

    def __init__(self, project: utils.interface.IProject, **kwargs) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __iter__(self) -> Iterator[IChangelogStatus]:
        while False:
            yield NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def changes_checker_class(
            self) -> Type[IChangelogChangesChecker]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def changes_checker(self) -> IChangelogChangesChecker:
        raise NotImplementedError


class IRSTCheck(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __call__(self, text: str) -> Optional[str]:
        raise NotImplementedError


class ICodeChecker(event.IReactive, metaclass=abstracts.Interface):
    pass
