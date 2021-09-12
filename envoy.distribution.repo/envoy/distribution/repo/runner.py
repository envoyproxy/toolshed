#!/bin/env python3

import argparse
import pathlib
import tarfile
from typing import Optional, Tuple

import abstracts

from envoy.base import runner, utils

from .abstract import ARepoBuildingRunner
from .exceptions import RepoError


@abstracts.implementer(ARepoBuildingRunner)
class RepoBuildingRunner:

    @property
    def archive(self) -> Optional[pathlib.Path]:
        """File path to archive the built repositories to."""
        return (
            pathlib.Path(self.args.archive)
            if self.args.archive
            else None)

    @property
    def packages(self) -> Tuple[pathlib.Path, ...]:
        """File paths to packages to build the repositories from."""
        return tuple(pathlib.Path(p) for p in self.args.packages)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("--packages", nargs="*")
        parser.add_argument("--archive", nargs="?")

    def create_archive(self, *paths) -> None:
        """Create an archive from the built repositories."""
        if not self.archive:
            self.log.warning(
                "No `--archive` argument provided, dry run only")
            return
        with tarfile.open(self.archive, "w") as tar:
            for path in paths:
                tar.add(path, arcname=".")

    def extract_packages(self):
        """Extract packages to build the repositories from."""
        for packages in self.packages:
            utils.extract(self.path, packages)

    @runner.cleansup
    @runner.catches(RepoError)
    async def run(self) -> Optional[int]:
        """Build and archive configured repositories."""
        self.extract_packages()
        self.create_archive(
            *await utils.async_list(
                self.published_repos,
                filter=lambda x: x))
