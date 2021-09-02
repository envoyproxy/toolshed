#!/bin/env python3

import argparse
import tarfile
from typing import List, Optional

import abstracts

from envoy.base import runner, utils

from .abstract import ARepoBuildingRunner
from .exceptions import RepoError


@abstracts.implementer(ARepoBuildingRunner)
class RepoBuildingRunner:

    @property
    def archive(self) -> Optional[str]:
        return self.args.archive

    @property
    def packages(self) -> List[str]:
        return self.args.packages

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("--packages", nargs="*")
        parser.add_argument("--archive", nargs="?")

    def create_archive(self, *paths) -> None:
        if not self.archive:
            self.log.warning(
                "No `--archive` argument provided, dry run only")
            return
        with tarfile.open(self.archive, "w") as tar:
            for path in paths:
                tar.add(path, arcname=".")

    def extract_packages(self):
        for packages in self.packages:
            utils.extract(self.path, packages)

    @runner.cleansup
    @runner.catches(RepoError)
    async def run(self) -> Optional[int]:
        self.extract_packages()
        self.create_archive(
            *await utils.async_list(
                self.published_repos,
                filter=lambda x: x))
