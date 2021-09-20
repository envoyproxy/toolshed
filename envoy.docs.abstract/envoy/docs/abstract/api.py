
import abc
import pathlib
import string
import tarfile
from functools import cached_property
from typing import Dict, Generator, Optional, Tuple, Union

import abstracts

from .builder import ADocsBuilder
from .formatter import ARSTFormatter


APIFilesGenerator = Generator[Tuple[str, bytes], None, None]
EmptyExtensionsDict = Dict[pathlib.Path, Union[str, bytes]]
ExtensionDetailsDict = Dict[str, str]

EMPTY_EXTENSION_DOCS_TEMPLATE = string.Template(
    """$header

$description

$reflink

This extension does not have a structured configuration, `google.protobuf.Empty
<https://developers.google.com/protocol-buffers/docs/reference/google.protobuf#empty>`_
should be used instead.

$extension
""")


class AAPIDocsBuilder(ADocsBuilder, metaclass=abstracts.Abstraction):

    @cached_property
    def api_extensions_root(self) -> pathlib.PurePosixPath:
        return self.api_root.joinpath("config")

    @property
    def api_files(self) -> APIFilesGenerator:
        with tarfile.open(self._api_files) as tar:
            for member in tar.getmembers():
                if member.isdir():
                    continue
                path = self.normalize_proto_path(member.path)
                if path:
                    content = tar.extractfile(member)
                    if content:
                        yield path, content.read()

    @cached_property
    def api_root(self) -> pathlib.PurePosixPath:
        return pathlib.PurePosixPath("api-v3")

    @property
    @abc.abstractmethod
    def empty_extensions(self) -> EmptyExtensionsDict:
        raise NotImplementedError

    @property
    def empty_extension_template(self) -> string.Template:
        return EMPTY_EXTENSION_DOCS_TEMPLATE

    @property
    @abc.abstractmethod
    def rst_formatter(self) -> ARSTFormatter:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def v3_proto_rst(self) -> Tuple[str, ...]:
        raise NotImplementedError

    async def build(self) -> None:
        for path, content in self.api_files:
            self.out(
                self.api_root.joinpath(path),
                content)
        for empty_path, empty_content in self.empty_extensions.items():
            self.out(
                self.api_extensions_root.joinpath(empty_path),
                empty_content)

    def canonical(self, path: str) -> str:
        if path.startswith("contrib/"):
            path = path[8:]
        if path.startswith("envoy/"):
            path = path[6:]
        return path

    def format_ref(self, ref):
        return self.rst_formatter.internal_link(
            "configuration overview", ref)

    def get_reflink(self, title: str, ref: Optional[str]) -> str:
        return (
            f"{title} {self.format_ref(ref)} ."
            if ref
            else "")

    def normalize_proto_path(self, path) -> Optional[str]:
        if "/pkg/" not in path:
            return None
        path = path.split('/pkg/')[1]
        if path in self.v3_proto_rst:
            return self.canonical(path)

    def render_empty_extension(
            self,
            extension: str,
            details: ExtensionDetailsDict) -> str:
        return self.empty_extension_template.substitute(
            header=self.rst_formatter.header(details['title'], "="),
            description=details.get('description', ''),
            reflink=self.get_reflink(details["title"], details.get("ref")),
            extension=self.rst_formatter.extension(extension))
