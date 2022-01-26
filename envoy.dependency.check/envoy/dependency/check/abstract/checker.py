"""Abstract dependency checker."""

import abc
import argparse
import json
import os
import pathlib
from functools import cached_property
from typing import Optional, Tuple, Type

import aiohttp

import gidgethub

import abstracts

from aio.api import github
from aio.run import checker
from aio.core.tasks import ConcurrentError, inflate

from envoy.dependency.check import abstract, exceptions, typing


class ADependencyChecker(
        checker.Checker,
        metaclass=abstracts.Abstraction):
    """Dependency checker."""

    checks = ("cves", "release_dates")

    @property
    @abc.abstractmethod
    def access_token(self) -> Optional[str]:
        """Github access token."""
        if self.args.github_token:
            return pathlib.Path(self.args.github_token).read_text().strip()
        return os.getenv('GITHUB_TOKEN')

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
            deps.append(self.dependency_class(k, v, self.github))
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

    @cached_property
    def disabled_checks(self):
        disabled = {}
        if not self.access_token:
            disabled["release_dates"] = "No Github access token supplied"
        return disabled

    @cached_property
    def github(self) -> github.GithubAPI:
        """Github API."""
        return github.GithubAPI(
            self.session, "",
            oauth_token=self.access_token)

    @cached_property
    def github_dependencies(self) -> Tuple["abstract.ADependency", ...]:
        """Tuple of dependencies."""
        deps = []
        for dep in self.dependencies:
            if not dep.github_url:
                urls = "\n".join(dep.urls)
                self.log.info(f"{dep.id} is not a GitHub repository\n{urls}")
                continue
            try:
                dep.github_version
            except exceptions.BadGithubURL as e:
                self.error("dependencies", [e.args[0]])
            else:
                deps.append(dep)
        return tuple(deps)

    @property
    def repository_locations_path(self) -> pathlib.Path:
        return pathlib.Path(self.args.repository_locations)

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return aiohttp.ClientSession()

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument('--github_token')
        parser.add_argument('--repository_locations')
        parser.add_argument('--cve_config')

    async def check_cves(self) -> None:
        """Scan for CVEs in a parsed NIST CVE database."""
        for dep in self.dependencies:
            await self.dep_cve_check(dep)

    async def check_release_dates(self) -> None:
        """Check recorded dates match for dependencies."""
        for dep in self.github_dependencies:
            await self.dep_date_check(dep)

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

    async def dep_date_check(
            self,
            dep: "abstract.ADependency") -> None:
        """Check dates for dependency."""
        if not await dep.release.date:
            self.error(
                "release_dates",
                [f"{dep.id} is a GitHub repository with no inferrable "
                 "release date"])
        elif await dep.release_date_mismatch:
            self.error(
                "release_dates",
                [f"Date mismatch: {dep.id} "
                 f"{dep.release_date} != {await dep.release.date}"])
        else:
            self.succeed(
                "release_dates",
                [f"Date matches ({dep.release_date}): {dep.id}"])

    async def on_checks_complete(self) -> int:
        await self.session.close()
        return await super().on_checks_complete()

    @checker.preload(
        when=["cves"],
        catches=[exceptions.CVECheckError])
    async def preload_cves(self) -> None:
        async for download in self.cves.downloads:
            self.log.debug(f"Preloaded cve data: {download}")

    @checker.preload(
        when=["release_dates"],
        catches=[ConcurrentError, gidgethub.GitHubException])
    async def preload_release_dates(self) -> None:
        preloader = inflate(
            self.github_dependencies,
            lambda d: (
                d.release.date, ))
        async for dep in preloader:
            self.log.debug(f"Preloaded release date: {dep.id}")
