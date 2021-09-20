
import abc
import pathlib
from functools import cached_property
from typing import Any, List, Dict

import abstracts

from .builder import ADocsBuilder
from .formatter import ARSTFormatter


ExtensionsMetadataDict = Dict[str, Dict[str, Any]]
ExtensionSecurityPosturesDict = Dict[str, List[str]]


class AExtensionsDocsBuilder(ADocsBuilder, metaclass=abstracts.Abstraction):

    @property
    @abc.abstractmethod
    def extensions_metadata(self) -> ExtensionsMetadataDict:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def rst_formatter(self) -> ARSTFormatter:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def security_postures(self) -> ExtensionSecurityPosturesDict:
        raise NotImplementedError

    @cached_property
    def security_rst_root(self) -> pathlib.PurePosixPath:
        return pathlib.PurePosixPath("intro/arch_overview/security")

    async def build(self) -> None:
        for sp, extensions in self.security_postures.items():
            self.out(
                self.security_rst_root.joinpath(f'secpos_{sp}.rst'),
                self.render(extensions))

    def render(self, extensions: List[str]) -> str:
        return "\n".join(
            self.rst_formatter.extension_list_item(
                extension,
                self.extensions_metadata[extension])
            for extension
            in sorted(extensions)
            if self.extensions_metadata[extension].get("status") != "wip")
