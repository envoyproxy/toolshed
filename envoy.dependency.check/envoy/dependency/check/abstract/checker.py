"""Abstract dependency checker."""

import abc
import argparse
import json
import os
import pathlib
import psutil
from functools import cached_property
from typing import Optional, Tuple, Type

import aiohttp

import gidgethub

import abstracts

from aio.api import github
from aio.run import checker
from aio.core.tasks import ConcurrentError, inflate

from envoy.dependency.check import abstract, exceptions, typing

NO_GITHUB_TOKEN_ERROR_MSG = ("No Github access token supplied "
                             "via environment variable `GITHUB_TOKEN` "
                             "or argument `--github_token`")


class ADependencyChecker(
        checker.Checker,
        metaclass=abstracts.Abstraction):
    """Dependency checker."""

    checks = (
        "cves",
        "release_dates",
        "release_issues",
        "release_sha",
        "releases")

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
    def cves(self) -> "abstract.ADependencyCVEs":
        return self.cves_class(
            self.dependencies,
            config_path=self.cve_config,
            session=self.session,
            loop=self.loop,
            pool=self.pool)

    @property  # type:ignore
    @abstracts.interfacemethod
    def cves_class(self) -> Type["abstract.ADependencyCVEs"]:
        """CVEs class."""
        raise NotImplementedError

    @cached_property
    def dep_ids(self) -> Tuple[str, ...]:
        """Tuple of dependency ids."""
        return tuple(dep.id for dep in self.dependencies)

    @cached_property
    def dependencies(self) -> Tuple["abstract.ADependency", ...]:
        """Tuple of dependencies."""
        deps = []
        for k, v in self.dependency_metadata.items():
            deps.append(
                self.dependency_class(
                    k, v,
                    self.github,
                    pool=self.pool,
                    loop=self.loop))
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
            disabled["release_dates"] = NO_GITHUB_TOKEN_ERROR_MSG
            disabled["release_issues"] = NO_GITHUB_TOKEN_ERROR_MSG
            disabled["releases"] = NO_GITHUB_TOKEN_ERROR_MSG
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

    @cached_property
    def issues(self) -> "abstract.AGithubDependencyIssues":
        """Dependency issues."""
        return self.issues_class(self.github)

    @property  # type:ignore
    @abstracts.interfacemethod
    def issues_class(self) -> Type["abstract.AGithubDependencyIssues"]:
        """Dependency issues class."""
        raise NotImplementedError

    @property
    def repository_locations_path(self) -> pathlib.Path:
        return pathlib.Path(self.args.repository_locations)

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return aiohttp.ClientSession()

    @cached_property
    def sha_preload_limit(self) -> int:
        return int(psutil.cpu_count() * 1.5)

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

    async def check_release_issues(self) -> None:
        """Check dependency issues."""
        await self.release_issues_labels_check()
        for dep in self.github_dependencies:
            await self.dep_release_issue_check(dep)
        await self.release_issues_missing_dep_check()
        await self.release_issues_duplicate_check()

    async def check_releases(self) -> None:
        """Check dependencies for new releases."""
        for dep in self.github_dependencies:
            await self.dep_release_check(dep)

    async def check_release_sha(self) -> None:
        """Check shas for new releases."""
        for dep in self.github_dependencies:
            await self.dep_release_sha_check(dep)

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
            self.warn(
                self.active_check,
                warnings)
        else:
            self.succeed(
                self.active_check,
                [f"No CVE vulnerabilities found: {dep.id}"])

    async def dep_date_check(
            self,
            dep: "abstract.ADependency") -> None:
        """Check dates for dependency."""
        if not await dep.release.date:
            self.error(
                self.active_check,
                [f"{dep.id} is a GitHub repository with no inferrable "
                 "release date"])
        elif await dep.release_date_mismatch:
            self.error(
                self.active_check,
                [f"Mismatch: {dep.id} "
                 f"{dep.release_date} != {await dep.release.date}"])
        else:
            self.succeed(
                self.active_check,
                [f"Match ({dep.release_date}): {dep.id}"])

    async def dep_release_issue_check(
            self,
            dep: "abstract.ADependency") -> None:
        """Check issues for dependency."""
        issue = (await self.issues.dep_issues).get(dep.id)
        newer_release = await dep.newer_release
        if not newer_release:
            if issue:
                # There is an open issue, but the dep is already
                # up-to-date.
                self.warn(
                    self.active_check,
                    [f"Stale issue: {dep.id} #{issue.number}"])
                if self.fix:
                    await self._dep_release_issue_close_stale(issue, dep)
            else:
                # No issue required
                self.succeed(
                    self.active_check,
                    [f"No issue required: {dep.id}"])
            return
        if issue:
            if issue.version == (await dep.newer_release).version:
                # Required issue exists
                self.succeed(
                    self.active_check,
                    [f"Issue exists (#{issue.number}): {dep.id}"])
                return
            # Existing issue is showing incorrect version
            self.warn(
                self.active_check,
                [f"Out-of-date issue (#{issue.number}): {dep.id} "
                 f"({issue.version} -> {newer_release.version})"])
        else:
            # Issue is required to be added
            self.warn(
                self.active_check,
                [f"Missing issue: {dep.id} ({newer_release.version})"])
        if self.fix:
            await self._dep_release_issue_create(issue, dep)

    async def dep_release_check(
            self,
            dep: "abstract.ADependency") -> None:
        """Check releases for dependency."""
        newer_release = await dep.newer_release
        if newer_release:
            self.warn(
                self.active_check,
                [f"Newer release ({newer_release.tag_name}): {dep.id}\n"
                 f"{dep.release_date} "
                 f"{dep.github_version_name}\n"
                 f"{await newer_release.date} "
                 f"{newer_release.tag_name} "])
        elif await dep.has_recent_commits:
            self.warn(
                self.active_check,
                [f"Recent commits ({await dep.recent_commits}): {dep.id}\n"
                 f"There have been {await dep.recent_commits} commits since "
                 f"{dep.github_version_name} landed on "
                 f"{dep.release_date}"])
        else:
            self.succeed(
                self.active_check,
                [f"Up-to-date ({dep.github_version_name}): {dep.id}"])

    async def dep_release_sha_check(
            self,
            dep: "abstract.ADependency") -> None:
        """Check sha for dependency."""
        if not await dep.release.sha:
            self.error(
                self.active_check,
                [f"Unable to generate release SHA: {dep.id}"])
        elif await dep.release_sha_mismatch:
            self.error(
                self.active_check,
                [f"Mismatch: {dep.id} "
                 f"{dep.release_sha} != {await dep.release.sha}"])
        else:
            self.succeed(
                self.active_check,
                [f"Match ({dep.display_sha}): {dep.id}"])

    async def release_issues_duplicate_check(self) -> None:
        """Check for duplicate issues for dependencies."""
        duplicates = False
        async for issue in self.issues.duplicate_issues:
            duplicates = True
            self.warn(
                self.active_check,
                [f"Duplicate issue for dependency (#{issue.number}): "
                 f"{issue.dep}"])
            if self.fix:
                await self._release_issue_close_duplicate(issue)
        if not duplicates:
            self.succeed(
                self.active_check,
                ["No duplicate issues found."])

    async def release_issues_labels_check(self) -> None:
        """Check expected labels are present."""
        missing = False
        for label in await self.issues.missing_labels:
            missing = True
            # TODO: make this a warning if `fix` and fix it
            self.error(
                self.active_check,
                [f"Missing label: {label}"])
        if not missing:
            self.succeed(
                self.active_check,
                [f"All ({len(self.issues.labels)}) "
                 "required labels are available."])

    async def release_issues_missing_dep_check(self) -> None:
        """Check for missing dependencies for issues."""
        closed = False
        issues = await self.issues.open_issues
        for issue in issues:
            if issue.dep not in self.dep_ids:
                closed = True
                self.warn(
                    self.active_check,
                    [f"Missing dependency (#{issue.number}): {issue.dep}"])
                if self.fix:
                    await self._release_issue_close_missing_dep(issue)
        if not closed:
            self.succeed(
                self.active_check,
                [f"All ({len(issues)}) issues have current dependencies."])

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
        unless=["releases", "release_issues"],
        catches=[ConcurrentError, gidgethub.GitHubException])
    async def preload_release_dates(self) -> None:
        preloader = inflate(
            self.github_dependencies,
            lambda d: (
                d.release.date, ))
        async for dep in preloader:
            self.log.debug(f"Preloaded release date: {dep.id}")

    @checker.preload(
        when=["release_issues"],
        blocks=["release_dates"],
        catches=[gidgethub.GitHubException])
    async def preload_release_issues(self) -> None:
        await self.issues.missing_labels
        await self.issues.dep_issues

    @checker.preload(
        when=["release_sha"],
        catches=[ConcurrentError, aiohttp.ClientError])
    async def preload_release_sha(self) -> None:
        preloader = inflate(
            self.github_dependencies,
            lambda d: (
                d.release.sha, ), limit=self.sha_preload_limit)
        async for dep in preloader:
            self.log.debug(f"Preloaded release sha: {dep.id}")

    @checker.preload(
        when=["releases", "release_issues"],
        blocks=["release_dates"],
        catches=[ConcurrentError, gidgethub.GitHubException])
    async def preload_releases(self) -> None:
        preloader = inflate(
            self.github_dependencies,
            lambda d: (
                d.newer_release,
                d.recent_commits))
        async for dep in preloader:
            self.log.debug(f"Preloaded release data: {dep.id}")

    async def _dep_release_issue_close_stale(
            self,
            issue: "abstract.AGithubDependencyIssue",
            dep: "abstract.ADependency") -> None:
        await issue.close()
        self.log.notice(
            f"Closed stale issue (#{issue.number}): {dep.id}\n"
            f"{issue.title}\n{issue.body}")

    async def _dep_release_issue_create(
            self,
            issue: "abstract.AGithubDependencyIssue",
            dep: "abstract.ADependency") -> None:
        if await self.issues.missing_labels:
            self.error(
                self.active_check,
                [f"Unable to create issue for {dep.id}: missing labels"])
            return
        new_issue = await self.issues.create(dep)
        self.log.notice(
            f"Created issue (#{new_issue.number}): "
            f"{dep.id} {new_issue.version}\n"
            f"{new_issue.title}\n{new_issue.body}")
        if not issue:
            return
        await new_issue.close_old(issue, dep)
        self.log.notice(
            f"Closed old issue (#{issue.number}): "
            f"{dep.id} {issue.version}\n"
            f"{issue.title}\n{issue.body}")

    async def _release_issue_close_duplicate(
            self,
            issue: "abstract.AGithubDependencyIssue") -> None:
        current_issue = (await self.issues.dep_issues)[issue.dep]
        await current_issue.close_duplicate(issue)
        self.log.notice(
            f"Closed duplicate issue (#{issue.number}): {issue.dep}\n"
            f" {issue.title}\n"
            f"current issue #({current_issue.number}):\n"
            f" {current_issue.title}")

    async def _release_issue_close_missing_dep(
            self,
            issue: "abstract.AGithubDependencyIssue") -> None:
        """Close an issue that has no current dependency."""
        await issue.close()
        self.log.notice(
            f"Closed issue with no current dependency (#{issue.number})")
