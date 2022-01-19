"""Abstract dependency checker."""

import abc
import argparse
import json
import pathlib
from functools import cached_property
from typing import Tuple, Type

import aiohttp

import abstracts

from aio.run import checker

from envoy.dependency.check import abstract, exceptions, typing


class ADependencyChecker(
        checker.Checker,
        metaclass=abstracts.Abstraction):
    """Dependency checker."""

    checks = ("cves", )

    @property
    def cve_config(self):
        return self.args.cve_config

    @cached_property
    def cves(self):
        return self.cves_class(
            self.dependencies,
            config_path=self.cve_config,
            session=self.session)

    @property  # type:ignore
    @abstracts.interfacemethod
    def cves_class(self) -> "abstract.ADependencyCVEs":
        """CVEs class."""
        raise NotImplementedError

    @cached_property
    def dependencies(self) -> Tuple["abstract.ADependency", ...]:
        """Tuple of dependencies."""
        deps = []
        for k, v in self.dependency_metadata.items():
            deps.append(self.dependency_class(k, v))
        return tuple(sorted(deps))

    @property  # type:ignore
    @abstracts.interfacemethod
    def dependency_class(self) -> Type["abstract.ADependency"]:
        """Dependency class."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def dependency_metadata(self) -> typing.DependenciesDict:
        """Dependency metadata (derived in Envoy's case from
        `repository_locations.bzl`)."""
        return json.loads(self.repository_locations_path.read_text())

    @property
    def repository_locations_path(self) -> pathlib.Path:
        return pathlib.Path(self.args.repository_locations)

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return aiohttp.ClientSession()

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument('--repository_locations')
        parser.add_argument('--cve_config')

    async def check_cves(self) -> None:
        """Scan for CVEs in a parsed NIST CVE database."""
        for dep in self.dependencies:
            await self.dep_cve_check(dep)

    async def dep_cve_check(
            self,
            dep: "abstract.ADependency") -> None:
        if not dep.cpe:
            self.log.info(f"No CPE listed for: {dep.id}")
            return
        warnings = []
        async for failing_cve in self.cves.dependency_check(dep):
            warnings.append(
                f'{failing_cve.format_failure(dep)}')
        if warnings:
            self.warn("cves", warnings)
        else:
            self.succeed("cves", [f"No CVEs found for: {dep.id}"])

    async def on_checks_complete(self) -> int:
        await self.session.close()
        return await super().on_checks_complete()

    @checker.preload(
        when=["cves"],
        catches=[exceptions.CVECheckError])
    async def preload_cves(self) -> None:
        async for download in self.cves.downloads:
            self.log.debug(f"Preloaded cve data: {download}")
