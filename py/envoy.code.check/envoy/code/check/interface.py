
import asyncio
import pathlib
from concurrent import futures
from typing import AsyncIterator, Iterator

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
            binaries: dict[str, str] | None = None,
            config: typing.YAMLConfigDict | None = None,
            loop: asyncio.AbstractEventLoop | None = None,
            pool: futures.Executor | None = None) -> None:
        raise NotImplementedError


class IFileCodeCheck(ICodeCheck, metaclass=abstracts.Interface):

    @property
    @abstracts.interfacemethod
    async def files(self) -> set[str]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def problem_files(self) -> dict[str, list[str]]:
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

    @property
    @abstracts.interfacemethod
    async def all_fuzzed(self) -> bool:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def extensions_schema(self) -> "typing.ExtensionsSchemaDict":
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def fuzz_test_path(self) -> pathlib.Path:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def metadata(self) -> "typing.ExtensionsMetadataDict":
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def metadata_errors(self) -> dict[str, tuple[str, ...]]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def owners_errors(self) -> dict[str, tuple[str, ...]]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def registration_errors(self) -> list[str]:
        raise NotImplementedError


class IFlake8Check(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IGlintCheck(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IGofmtCheck(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IShellcheckCheck(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IYamllintCheck(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IYapfCheck(IFileCodeCheck, metaclass=abstracts.Interface):
    pass


class IRuntimeGuardsCheck(IProjectCodeCheck, metaclass=abstracts.Interface):

    @property
    @abstracts.interfacemethod
    async def missing(self) -> set[str]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def status(self) -> AsyncIterator[tuple[str, bool | None]]:
        raise NotImplementedError


class IChangelogChangesChecker(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def check_sections(
            self,
            version: _version.Version,
            sections: utils.typing.ChangelogChangeSectionsDict) -> (
                tuple[str, ...]):
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

    @property
    @abstracts.interfacemethod
    def changes_checker_class(
            self) -> type[IChangelogChangesChecker]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def changes_checker(self) -> IChangelogChangesChecker:
        raise NotImplementedError


class IRSTCheck(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __call__(self, text: str) -> str | None:
        raise NotImplementedError


class ICodeChecker(event.IReactive, metaclass=abstracts.Interface):
    pass
