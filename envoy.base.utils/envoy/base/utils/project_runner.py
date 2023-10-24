
import json
import os
import pathlib
from functools import cached_property
from typing import Optional

from packaging import version as _version

import aiohttp
from frozendict import frozendict

from aio.api.github import exceptions as github_exceptions
from aio.run import runner

from envoy.base import utils
from envoy.base.utils import exceptions, interface, typing


ENV_GITHUB_TOKEN = "GITHUB_TOKEN"
# TODO: move these to config
ENVOY_DOCKER_IMAGE = (
    "https://hub.docker.com/r/envoyproxy/envoy/tags?page=1&name=")
ENVOY_DOCS = "https://www.envoyproxy.io/docs/envoy"
ENVOY_REPO = "https://github.com/envoyproxy/envoy"
NOTIFY_MSGS: frozendict = frozendict(
    release=(
        "Release created ({change[release][version]}): "
        "{change[release][date]}"),
    dev="Repo set to dev ({change[dev][version]})",
    sync="Repo synced",
    publish="""
Repo published{change[publish][dry_run]}: {change[publish][url]}\n
{change[publish][body]}
""",
    trigger="Workflow ({change[trigger][workflow]}) triggered")
COMMIT_MSGS: frozendict = frozendict(
    release="""
repo: Release {version_string}

{change[release][message]}
**Docker images**:
    {envoy_docker_image}{version_string}
**Docs**:
    {envoy_docs}/{version_string}/
**Release notes**:
    {envoy_docs}/{version_string}/version_history/{minor_version}/{version_string}
**Full changelog**:
    {envoy_repo}/compare/{previous_release_version}...{version_string}

""",
    dev="repo: Dev {version_string}",
    sync="repo: Sync")


class BaseProjectRunner(runner.Runner):

    @property
    def github_token(self) -> Optional[str]:
        """Github access token."""
        if self.args.github_token:
            return pathlib.Path(self.args.github_token).read_text().strip()
        return os.getenv(ENV_GITHUB_TOKEN)

    @cached_property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.args.path)

    @cached_property
    def project(self) -> interface.IProject:
        return utils.Project(
            path=self.path,
            session=self.session,
            repo=self.repo_name,
            github_token=self.github_token)

    @property
    def repo_name(self) -> Optional[str]:
        return self.args.repo

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return aiohttp.ClientSession()


class ProjectRunner(BaseProjectRunner):

    @property
    def author(self) -> str:
        return (
            self.args.release_author
            if self.args.command in ["release"]
            else "")

    @property
    def signoffs(self) -> set[str]:
        return (
            set(self.args.release_signoff)
            if (self.args.command in ["release"]
                and self.args.release_signoff)
            else set())

    @property
    def command(self) -> bool:
        return self.args.command

    @property
    def nocommit(self) -> bool:
        return (
            self.args.command in ["publish", "trigger"]
            or self.args.nocommit)

    @property
    def nosync(self) -> bool:
        return self.args.nosync

    @property
    def patch(self) -> bool:
        return self.args.patch

    @property
    def release_message(self) -> str:
        return (
            pathlib.Path(message_path).read_text()
            if (message_path := self.args.release_message_path)
            else "")

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "command",
            choices=["sync", "release", "dev", "publish", "trigger"])
        parser.add_argument("path", default=".")
        parser.add_argument("--app-key", default="GITHUB_APP_KEY")
        parser.add_argument("--app-keyfile", default="")
        parser.add_argument("--github_token")
        parser.add_argument("--nosync", action="store_true")
        parser.add_argument("--nocommit", action="store_true")
        parser.add_argument("--patch", action="store_true")
        parser.add_argument("--repo", default="")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--release-author", default="")
        parser.add_argument("--release-message-path", default="")
        parser.add_argument("--release-signoff", nargs="*")
        parser.add_argument("--publish-assets", default="")
        parser.add_argument("--publish-commitish", default="")
        parser.add_argument("--publish-commit-message", action="store_true")
        parser.add_argument("--publish-dev", action="store_true")
        parser.add_argument("--publish-latest", action="store_true")
        parser.add_argument("--publish-generate-notes", action="store_true")
        parser.add_argument("--trigger-ref", default="")
        parser.add_argument("--trigger-app-id", default="")
        parser.add_argument("--trigger-installation-id", default="")
        parser.add_argument("--trigger-workflow", default="")
        parser.add_argument("--trigger-inputs", default="")

    async def commit(
            self,
            change: typing.ProjectChangeDict) -> None:
        msg = self.msg_for_commit(change)
        commit = self.project.commit(
            change, msg,
            author=self.author)
        async for path in commit:
            self.log.info(f"[git] add: {path}")
        self.log.info(f"[git] commit: \"{msg}\"")

    async def handle_action(self) -> typing.ProjectChangeDict:
        change: typing.ProjectChangeDict = {}
        if self.command == "publish":
            return dict(
                publish=await self.run_publish(
                    dry_run=self.args.dry_run,
                    assets=self.args.publish_assets,
                    commitish=self.args.publish_commitish,
                    publish_commit_message=self.args.publish_commit_message,
                    dev=self.args.publish_dev,
                    latest=self.args.publish_latest))
        if self.command == "dev":
            change["dev"] = await self.run_dev()
        if self.command == "release":
            change["release"] = await self.run_release(
                release_message=self.release_message)
        if not self.nosync and self.command in ["dev", "release", "sync"]:
            change["sync"] = await self.run_sync()
        if self.command == "trigger":
            change["trigger"] = await self.run_trigger()
        return change

    def msg_for_commit(self, change: typing.ProjectChangeDict) -> str:
        kwargs = dict(
            change=change,
            envoy_docker_image=ENVOY_DOCKER_IMAGE,
            envoy_docs=ENVOY_DOCS,
            envoy_repo=ENVOY_REPO)
        # TODO(phlax): improve tests here
        if change.get("release", {}).get("version"):
            release_version = _version.Version(change["release"]["version"])
            minor_version = utils.minor_version_for(release_version)
            previous_version = self._previous_version(release_version)
            kwargs.update(
                dict(version_string=f"v{release_version}",
                     minor_version=f"v{minor_version}",
                     previous_release_version=(f"v{previous_version}")))
        if change.get("dev", {}).get("version"):
            release_version = _version.Version(change["dev"]["version"])
            kwargs.update(
                dict(version_string=f"v{release_version.base_version}"))
        msg = COMMIT_MSGS[self.command].format(**kwargs)
        for signoff in self.signoffs:
            if signoff != self.author:
                msg = f"{msg}\nSigned-off-by: {signoff}"
        return msg

    def notify_complete(self, change: typing.ProjectChangeDict) -> None:
        self.log.notice(
            NOTIFY_MSGS[self.command].format(
                change=change).lstrip())

    @runner.cleansup
    @runner.catches(
        (exceptions.DevError,
         exceptions.ReleaseError,
         exceptions.PublishError,
         github_exceptions.TagError,
         github_exceptions.TagExistsError))
    async def run(self) -> None:
        change = await self.handle_action()
        if not self.nocommit:
            await self.commit(change)
        self.notify_complete(change)

    async def run_dev(self) -> typing.ProjectDevResultDict:
        change = await self.project.dev(patch=self.patch)
        self.log.success(f"[version] {change['version']}")
        self.log.success(
            f"[changelog] add: {change['old_version']}")
        return change

    async def run_publish(self, **kwargs) -> typing.ProjectPublishResultDict:
        change = None
        dry_run = (
            " (dry run)"
            if kwargs.get("dry_run")
            else "")
        async for result in self.project.publish(**kwargs):
            if not change:
                change = result
                self.log.success(
                    f"[release] Release ({change['tag_name']}) "
                    f"created{dry_run} from branch/commit: "
                    f"{change['commitish']}")
                continue
            if "error" in result:
                self.log.error(
                    f"[release] Something went wrong uploading{dry_run}: "
                    f"{result['name']} -> {result['url']}\n{result['error']}")
                continue
            self.log.success(
                f"[release] Artefact uploaded{dry_run}: "
                f"{result['name']} -> {result['url']}")
        if not change:
            raise exceptions.PublishError("Unknown publishing error")
        return utils.typed(typing.ProjectPublishResultDict, change)

    async def run_release(
            self,
            author: str = "",
            release_message: str = "") -> typing.ProjectReleaseResultDict:
        change = await self.project.release()
        self.log.success(f"[version] {change['version']}")
        self.log.success(f"[changelog] current: {change['date']}")
        change["message"] = (
            f"{release_message.strip()}\n"
            if release_message
            else "")
        return change

    async def run_sync(self) -> typing.ProjectSyncResultDict:
        change = await self.project.sync()
        self._log_changelog(change["changelog"])
        self._log_inventory(change["inventory"])
        return change

    async def run_trigger(self, **kwargs) -> typing.ProjectTriggerResultDict:
        if self.args.app_keyfile:
            key = pathlib.Path(self.args.app_keyfile).read_bytes()
        else:
            key = os.environ[self.args.app_key].encode("utf-8")
        inputs = (
            json.loads(self.args.trigger_inputs)
            if self.args.trigger_inputs
            else {})
        data = dict(
            ref=self.args.trigger_ref,
            inputs=inputs)
        return await self.project.trigger(
            workflow=self.args.trigger_workflow,
            app_id=self.args.trigger_app_id,
            installation_id=self.args.trigger_installation_id,
            key=key,
            data=data)

    def _log_changelog(self, results: typing.SyncResultDict) -> None:
        if not results:
            self.log.success("[changelog] up to date")
        for version, result in results.items():
            self.log.success(f"[changelog] add: {version}")

    def _log_inventory(self, results: typing.SyncResultDict) -> None:
        if not results:
            self.log.success("[inventory] up to date")
        for version, result in results.items():
            if result:
                self.log.success(
                    "[inventory] update: "
                    f"{utils.minor_version_for(version)} -> {version}")
            else:
                self.log.warning(
                    "[inventory] newer version available "
                    f"({version}), but no inventory found")

    def _previous_version(
            self,
            version: _version.Version) -> _version.Version:
        return _version.Version(
            f"{version.major}."
            f"{version.minor - (1 if version.micro == 0 else 0)}."
            f"{version.micro - (1 if version.micro != 0 else 0)}")


class ProjectDataRunner(BaseProjectRunner):

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument("path", default=".")
        parser.add_argument("--repo", default="")
        parser.add_argument("--github_token")

    @runner.cleansup
    async def run(self) -> None:
        print(await self.project.json_data)
