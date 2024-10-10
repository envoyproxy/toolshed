
import io
import json
import logging
import zipfile
from typing import Awaitable, AsyncIterator

import aiohttp

import abstracts

from aio.api import github
from aio.core.functional import async_property
from aio.core.tasks import concurrent

from envoy.ci.report import exceptions

URL_GH_REPO_ACTION_ENV_ARTIFACT = "actions/runs/{wfid}/artifacts?name=env"
URL_GH_REPO_ACTIONS = "actions/runs?per_page=100"
URL_GH_REPO_ACTIONS_REQUEST = (
    "actions/workflows/request.yml/runs?head_sha={sha}")
GH_ACTION_REQUEST_FILE = "env.json"

log = logging.getLogger(__name__)


class ACIRuns(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            repo: github.interface.IGithubRepo,
            filters: dict[str, str] | None = None,
            ignored: dict | None = None,
            sort_ascending: bool | None = None) -> None:
        self.repo = repo
        self.filters: dict[str, str] = filters or {}
        self.ignored: dict[str, dict] = ignored or {}
        self._sort_ascending = (
            False
            if sort_ascending is None
            else sort_ascending)

    @async_property
    async def as_dict(self) -> dict:
        return self._sorted(await self._to_dict())

    @async_property(cache=True)
    async def check_runs(self) -> dict:
        result: dict = {}
        async for info in concurrent(self._check_run_fetches):
            if not info:
                continue
            commit, event, info = info
            result[commit] = result.get(commit, {})
            result[commit][event] = result[commit].get(event, [])
            result[commit][event].append(info)
        return result

    @async_property(cache=True)
    async def envs(self) -> dict:
        artifacts: dict = {}
        async for result in concurrent(self._env_fetches):
            if not result:
                continue
            env, (wfid, sha, event) = result
            artifacts[sha] = artifacts.get(sha, {})
            artifacts[sha][event] = artifacts[sha].get(event, {})
            artifacts[sha][event][wfid] = env
        return artifacts

    @property
    def github_headers(self) -> dict[str, str]:
        return {"Authorization": f"token {self.repo.github.api.oauth_token}"}

    @async_property(cache=True)
    async def shas(self) -> set[str]:
        return set(
            _wf["head_sha"]
            for _wf
            in (await self.workflows).values())

    @property
    def sort_ascending(self) -> bool:
        return self._sort_ascending

    @async_property(cache=True)
    async def workflow_requests(self) -> dict:
        wfids: dict = {}
        to_fetch = [
            self.fetch_requests(sha)
            for sha
            in await self.shas]
        async for requests in concurrent(to_fetch):
            for request in requests:
                (sha, event, wfid) = request
                wfids[sha] = wfids.get(sha, {})
                wfids[sha][event] = wfids[sha].get(event, [])
                wfids[sha][event].append(wfid)
        return wfids

    @async_property(cache=True)
    async def workflows(self) -> dict:
        return {
            wf["id"]: dict(
                head_sha=wf["head_sha"],
                name=wf["name"],
                status=wf["status"],
                event=wf["event"],
                conclusion=wf["conclusion"])
            async for wf
            in self.repo.getiter(
                self.workflows_url,
                iterable_key="workflow_runs")
            if (not self.ignored
                or (wf["name"]
                    not in self.ignored.get("workflows", [])))}

    @property
    def workflows_url(self) -> str:
        filters = [
            f"{k}={v}"
            for k, v
            in self.filters.items()]
        return (
            URL_GH_REPO_ACTIONS
            if not filters
            else f"{URL_GH_REPO_ACTIONS}&{'&'.join(filters)}")

    async def fetch_check(
            self,
            commit: str,
            event: str,
            info: dict) -> tuple[str, str, dict] | None:
        check_run = await self.repo.getitem(f"check-runs/{info['check-id']}")
        not_found = (
            not check_run.get("external_id")
            or int(check_run["external_id"]) not in await self.workflows)
        if not_found:
            return None
        del info["action"]
        info.pop("advice", None)
        info["external_id"] = check_run["external_id"]
        return commit, event, info

    async def fetch_request_env(
            self,
            wfid: int,
            sha: str,
            event: str) -> tuple[dict, tuple[int, str, str]] | None:
        if fetch_artifact := await self._fetch_env_artifact(wfid):
            async with fetch_artifact as response:
                if response.status != 200:
                    raise exceptions.RequestArtifactFetchError(
                        f"Failed to download: {response.status}")
                return (
                    self.parse_env(await response.read()),
                    (wfid, sha, event))

    async def fetch_requests(self, sha: str) -> list[tuple[str, str, str]]:
        return [
            (sha, workflow_run["event"], workflow_run["id"])
            async for workflow_run
            in self.repo.getiter(
                URL_GH_REPO_ACTIONS_REQUEST.format(sha=sha),
                iterable_key="workflow_runs")
            if (not self.ignored
                or (workflow_run["event"]
                    not in self.ignored.get("triggers", [])))]

    def parse_env(self, data: bytes) -> dict:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for file_info in z.infolist():
                if file_info.filename != GH_ACTION_REQUEST_FILE:
                    continue
                with z.open(file_info) as file:
                    wfdata = json.load(file)
                    return dict(
                        checks=wfdata["checks"],
                        request=wfdata["request"])
        raise exceptions.RequestArtifactFetchError(
            "Failed to find env.json in download")

    @async_property
    async def _check_run_fetches(self) -> AsyncIterator[Awaitable]:
        for commit, request in (await self.workflow_requests).items():
            for event, event_info in (await self.envs).get(commit, {}).items():
                for request_id, data in event_info.items():
                    for check, info in data["checks"].items():
                        if info["action"] != "RUN":
                            continue
                        yield self.fetch_check(commit, event, info)

    @async_property
    async def _env_fetches(self) -> AsyncIterator[Awaitable]:
        for sha, events in (await self.workflow_requests).items():
            for event, wfids in events.items():
                for wf in wfids:
                    if fetch_request := self.fetch_request_env(wf, sha, event):
                        yield fetch_request

    async def _fetch_env_artifact(
            self, wfid: int) -> aiohttp.ClientResponse | None:
        if artifact_url := await self._resolve_env_artifact_url(wfid):
            return self.repo.github.session.get(
                artifact_url,
                headers=self.github_headers)

    async def _resolve_env_artifact_url(self, wfid: int) -> str | None:
        try:
            return (
                await self.repo.getitem(
                    URL_GH_REPO_ACTION_ENV_ARTIFACT.format(
                        wfid=wfid)))["artifacts"][0]["archive_download_url"]
        except IndexError:
            log.warning(f"Unable to find request artifact: {wfid}")

    def _sorted(self, runs: dict) -> dict:
        max_or_min = (
            min
            if self.sort_ascending
            else max)
        return dict(
            sorted(
                ((k,
                  sorted(
                      v,
                      key=lambda event: event["request"]["started"],
                      reverse=not self.sort_ascending))
                 for k, v in runs.items()),
                key=lambda item: max_or_min(
                    x["request"]["started"]
                    for x in item[1]),
                reverse=not self.sort_ascending))

    async def _to_dict(self) -> dict:
        return {
            commit: requests
            for commit, request in (await self.workflow_requests).items()
            if (requests := await self._to_list_request(commit, request))}

    async def _to_list_request(self, commit: str, request: dict) -> list[dict]:
        return [
            {"event": event,
             "request": (await self.envs)[commit][event][req]["request"],
             "request_id": req,
             "check_name": check_run["name"],
             "workflow_id": check_run["external_id"],
             "workflow": (await self.workflows)[int(check_run["external_id"])]}
            for event, requests in request.items()
            for check_run in (
                    await self.check_runs).get(
                        commit, {}).get(event, [])
            for req in requests]
