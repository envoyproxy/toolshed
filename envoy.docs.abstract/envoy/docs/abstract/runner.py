
import abc
import argparse
import io
import pathlib
import tarfile
from functools import cached_property
from typing import Any, Dict, Tuple, Type, Union

import abstracts

from envoy.base import runner, utils

from .builder import ADocsBuilder


BuildersDict = Dict[str, Any]


class ADocsBuildingRunner(runner.AsyncRunner, metaclass=abstracts.Abstraction):
    _builders: Tuple[Tuple[str, Type[ADocsBuilder]], ...] = ()

    @classmethod
    def register_builder(cls, name: str, util: Type[ADocsBuilder]) -> None:
        """Register a repo type."""
        cls._builders = (
            getattr(cls, "_builders")
            + ((name, util),))

    @property
    def api_rst_files(self):
        return self.args.api_files

    @property
    @abc.abstractmethod
    def builders(self) -> BuildersDict:
        return {
            k: v(self.write_tar, self.api_rst_files)
            for k, v in self._builders}

    @cached_property
    def tar(self):
        return tarfile.open(self.args.out_path, "w")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "api_files",
            help="Tarball containing Protobuf API rst files")
        parser.add_argument(
            "--out_path",
            help="Outfile to tar rst files into")

    @abc.abstractmethod
    async def run(self):
        for builder in self.builders.values():
            await builder.build()
        self.tar.close()

    def write_tar(
            self,
            path: Union[str, pathlib.Path],
            content: Union[str, bytes]) -> None:
        tarinfo = tarfile.TarInfo(str(path))
        tarinfo.size = len(content)
        self.tar.addfile(tarinfo, io.BytesIO(utils.to_bytes(content)))
