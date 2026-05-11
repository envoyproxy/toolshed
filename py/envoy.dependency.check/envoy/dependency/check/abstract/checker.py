"""Abstract dependency checker."""

import abc
import argparse
import json
import os
import pathlib
import re
from functools import cached_property
from typing import Any

import aiohttp

import gidgethub

import abstracts

from aio.api import github as _github
from aio.run import checker, runner
from aio.core.tasks import ConcurrentError, inflate

from envoy.dependency.check import abstract, exceptions, typing


GITHUB_API_URL = "https://api.github.com"
NO_GITHUB_TOKEN_ERROR_MSG = (
    "No Github access token supplied "
    "via environment variable `GITHUB_TOKEN` "
    "or argument `--github_token`")
NO_ISSUE_DEPENDENCIES = r"com_google_protobuf_protoc_[a-zA-Z0-9_]+$"
HTTP_SESSION_TIMEOUT_SECONDS = 300
PACKAGE_NAME = "envoy.dependency.check"
REQUIRED_DEPENDENCY_METADATA_KEYS = (
    "release_date", "version", "urls", "sha256")


def _http_user_agent() -> str:
    for parent in pathlib.Path(__file__).resolve().parents:
        version_path = parent.joinpath("VERSION")
        if not version_path.is_file():
            continue
        try:
            return f"{PACKAGE_NAME}/{version_path.read_text().strip()}"
        except OSError:
            break
    return PACKAGE_NAME


HTTP_USER_AGENT = _http_user_agent()


class ADependencyChecker(
        checker.Checker,
        metaclass=abstracts.Abstraction):
    """Dependency checker."""

    checks = (
        "release_dates",
        "release_issues",
        "releases")

    REQUIRED_DEPENDENCY_METADATA_KEYS = REQUIRED_DEPENDENCY_METADATA_KEYS

    @property
    @abc.abstractmethod
    def access_token(self) -> str | None:
        """Github access token."""
        if self.args.github_token:
            try:
                return pathlib.Path(self.args.github_token).read_text().strip()
            except OSError as e:
                raise exceptions.GithubTokenError(
                    f"Cannot read GitHub token from "
                    f"{self.args.github_token}: {e}")
        if token := os.getenv('GITHUB_TOKEN'):
            return token
        raise exceptions.GithubTokenError(NO_GITHUB_TOKEN_ERROR_MSG)

    @cached_property
    def dep_ids(self) -> tuple[str, ...]:
        """Tuple of dependency ids."""
        return tuple(dep.id for dep in self.dependencies)

    @cached_property
    def dependencies(self) -> tuple["abstract.ADependency", ...]:
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

    @property
    @abstracts.interfacemethod
    def dependency_class(self) -> type["abstract.ADependency"]:
        """Dependency class."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def dependency_metadata(self) -> typing.DependenciesDict:
        """Dependency metadata (derived in Envoy's case from
        `repository_locations.bzl`)."""
        data = json.loads(self.repository_locations_path.read_text())
        self._validate_dependency_metadata(data)
        return data

    @cached_property
    def github(self) -> _github.IGithubAPI:
        """Github API."""
        return _github.GithubAPI(
            self.session, GITHUB_API_URL,
            oauth_token=self.access_token)

    @cached_property
    def github_dependencies(self) -> tuple["abstract.ADependency", ...]:
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
    def issues(self) -> _github.IGithubIssuesTracker:
        """Dependency issues."""
        return self.issues_class(self.github)

    @property
    @abstracts.interfacemethod
    def issues_class(self) -> type[_github.IGithubIssuesTracker]:
        """Dependency issues class."""
        raise NotImplementedError

    @property
    def repository_locations_path(self) -> pathlib.Path:
        return pathlib.Path(self.args.repository_locations)

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=HTTP_SESSION_TIMEOUT_SECONDS),
            headers={"User-Agent": HTTP_USER_AGENT})

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument('--github_token')
        parser.add_argument('--repository_locations')

    async def check_release_dates(self) -> None:
        """Check recorded dates match for dependencies."""
        for dep in self.github_dependencies:
            await self.dep_date_check(dep)

    async def check_release_issues(self) -> None:
        """Check dependency issues."""
        try:
            await self.release_issues_labels_check()
            for dep in self.github_dependencies:
                await self.dep_release_issue_check(dep)
            await self.release_issues_missing_dep_check()
            await self.release_issues_duplicate_check()
        except _github.exceptions.IssueCreateError as e:
            self.error(
                self.active_check,
                [f"Release issues check failed: {e}"])

    async def check_releases(self) -> None:
        """Check dependencies for new releases."""
        for dep in self.github_dependencies:
            await self.dep_release_check(dep)

    async def dep_date_check(
            self,
            dep: "abstract.ADependency") -> None:
        """Check dates for dependency."""
        if not await dep.release.date:
            self.warn(
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
        issue = (await self.issues["releases"].issues).get(dep.id)

        # TODO: move the exclusion logic to tracker
        if self._no_dep_issues.match(dep.id):
            if issue:
                # There is an open issue, but the dep should be ignored.
                self.warn(
                    self.active_check,
                    [f"Incorrect issue: {dep.id} #{issue.number}"])
                if self.fix:
                    await self._dep_release_issue_close_stale(issue, dep)
            else:
                # No issue required
                self.log.info(
                    f"Ignored by dependency issue tracker: {dep.id}")
            return

        if not (newer_release := await dep.newer_release):
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
            if issue.version == newer_release.version:
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
        if newer_release := await dep.newer_release:
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

    async def release_issues_duplicate_check(self) -> None:
        """Check for duplicate issues for dependencies."""
        duplicates = False
        async for issue in self.issues["releases"].duplicate_issues:
            duplicates = True
            self.warn(
                self.active_check,
                [f"Duplicate issue for dependency (#{issue.number}): "
                 f"{issue.key}"])
            if self.fix:
                await self._release_issue_close_duplicate(issue)
        if not duplicates:
            self.succeed(
                self.active_check,
                ["No duplicate issues found."])

    async def release_issues_labels_check(self) -> None:
        """Check expected labels are present."""
        missing = False
        release_issues = self.issues["releases"]
        for label in await release_issues.missing_labels:
            missing = True
            if not self.fix:
                self.error(
                    self.active_check,
                    [f"Missing label: {label}"])
                continue
            try:
                await release_issues.create_label(label)
            except (
                    ConnectionError,
                    OSError,
                    PermissionError,
                    gidgethub.GitHubException) as e:
                self.error(
                    self.active_check,
                    [f"Missing label: {label} "
                     f"(create failed: {type(e).__name__}: {e})"])
            else:
                self.warn(
                    self.active_check,
                    [f"Missing label created: {label}"])
        if not missing:
            self.succeed(
                self.active_check,
                [f"All ({len(self.issues['releases'].labels)}) "
                 "required labels are available."])

    async def release_issues_missing_dep_check(self) -> None:
        """Check for missing dependencies for issues."""
        closed = False
        issues = await self.issues["releases"].open_issues
        for issue in issues:
            if issue.key not in self.dep_ids:
                closed = True
                self.warn(
                    self.active_check,
                    [f"Missing dependency (#{issue.number}): {issue.key}"])
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
        await self.issues["releases"].missing_labels
        await self.issues["releases"].issues

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

    @runner.catches(
        (exceptions.GithubTokenError, exceptions.DependencyMetadataError))
    async def run(self) -> int | None:
        return await super().run()

    @cached_property
    def _no_dep_issues(self) -> re.Pattern[str]:
        return re.compile(NO_ISSUE_DEPENDENCIES)

    def _validate_dependency_metadata(self, data: dict[str, Any]) -> None:
        errors: list[str] = []
        for dep_id, meta in data.items():
            if not isinstance(meta, dict):
                errors.append(
                    f"{dep_id}: metadata must be a mapping, "
                    f"got {type(meta).__name__}")
                continue
            missing = [
                k for k in self.REQUIRED_DEPENDENCY_METADATA_KEYS
                if k not in meta]
            if missing:
                errors.append(
                    f"{dep_id}: missing required keys: "
                    f"{', '.join(missing)}")
        if errors:
            raise exceptions.DependencyMetadataError(
                "Invalid dependency metadata:\n  "
                + "\n  ".join(errors))

    async def _dep_release_issue_close_stale(
            self,
            issue: "abstract.AGithubDependencyReleaseIssue",
            dep: "abstract.ADependency") -> None:
        await issue.close()
        self.log.notice(
            f"Closed stale issue (#{issue.number}): {dep.id}\n"
            f"{issue.title}\n{issue.body}")

    async def _dep_release_issue_create(
            self,
            issue: "abstract.AGithubDependencyReleaseIssue",
            dep: "abstract.ADependency") -> None:
        if await self.issues["releases"].missing_labels:
            self.error(
                self.active_check,
                [f"Unable to create issue for {dep.id}: missing labels"])
            return
        new_issue = await self.issues["releases"].create(dep=dep)
        self.log.notice(
            f"Created issue (#{new_issue.number}): "
            f"{dep.id} {new_issue.version}\n"
            f"{new_issue.title}\n{new_issue.body}")
        if not issue:
            return
        await new_issue.close_old(issue, dep=dep)
        self.log.notice(
            f"Closed old issue (#{issue.number}): "
            f"{dep.id} {issue.version}\n"
            f"{issue.title}\n{issue.body}")

    async def _release_issue_close_duplicate(
            self,
            issue: "abstract.AGithubDependencyReleaseIssue") -> None:
        current_issue = (
            await self.issues["releases"].issues)[issue.key]
        await current_issue.close_duplicate(issue)
        self.log.notice(
            f"Closed duplicate issue (#{issue.number}): {issue.key}\n"
            f" {issue.title}\n"
            f"current issue #({current_issue.number}):\n"
            f" {current_issue.title}")

    async def _release_issue_close_missing_dep(
            self,
            issue: "abstract.AGithubDependencyReleaseIssue") -> None:
        """Close an issue that has no current dependency."""
        await issue.close()
        self.log.notice(
            f"Closed issue with no current dependency (#{issue.number})")
