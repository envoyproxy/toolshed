import pathlib
import tarfile
from functools import cached_property
from typing import Dict, Iterator, Union

import aiohttp

from envoy.base import utils

from envoy.github.abstract import (
    AGithubActionAssetsFetcher, AGithubActionAssetsPusher,
    GithubActionError)
from envoy.github.action import stream


class GithubActionAssetsFetcher(AGithubActionAssetsFetcher):

    def __exit__(self, *args) -> None:
        # TODO(phlax): make this non-blocking
        with tarfile.open(super().path, self.write_mode) as tar:
            tar.add(self.path, arcname=self.version)
        super().__exit__(*args)

    @property
    def concurrency(self) -> int:
        return super().concurrency

    @cached_property
    def is_tarlike(self) -> bool:
        return utils.is_tarlike(super().path)

    @property
    def out_exists(self) -> bool:
        return super().path.exists() and not self.append

    @cached_property
    def path(self) -> pathlib.Path:
        if self.out_exists:
            self.fail(
                f"Output directory exists: {super().path}"
                if not self.is_tarlike
                else f"Output tarball exists: {super().path}")
        return (
            pathlib.Path(self.tempdir.name)
            if self.is_tarlike
            else super().path)

    async def download(
            self,
            asset: Dict) -> Dict[str, Union[str, pathlib.Path]]:
        return await self.save(
            asset["asset_type"], asset["name"],
            await self.session.get(asset["browser_download_url"]))

    async def save(
            self,
            asset_type: str,
            name: str,
            download: aiohttp.ClientResponse) -> Dict[
                str, Union[str, pathlib.Path]]:
        outfile = self.path.joinpath(asset_type, name)
        outfile.parent.mkdir(exist_ok=True)
        async with stream.writer(outfile) as f:
            await f.stream_bytes(download)
        result: Dict[str, Union[str, pathlib.Path]] = dict(
            name=name,
            outfile=outfile)
        if download.status != 200:
            result["error"] = self.fail(
                f"Failed downloading, got response:\n{download}")
        return result


class GithubActionAssetsPusher(AGithubActionAssetsPusher):
    _artefacts_glob = "**/*{version}*"
    file_exts = {"deb", "changes", "rpm"}

    @property
    def artefacts(self) -> Iterator[pathlib.Path]:
        globs = self.path.glob(
            self._artefacts_glob.format(version=self.version))
        for match in globs:
            if match.suffix[1:] in self.file_exts:
                yield match

    @property
    def concurrency(self) -> int:
        return super().concurrency

    @cached_property
    def is_dir(self) -> bool:
        return super().path.is_dir()

    @cached_property
    def is_tarball(self) -> bool:
        return tarfile.is_tarfile(super().path)

    @cached_property
    def path(self) -> pathlib.Path:
        if not self.is_tarball and not self.is_dir:
            raise GithubActionError(
                f"Unrecognized target '{super().path}', should either be a "
                "directory or a tarball containing packages")
        # TODO(phlax): make this non-blocking
        return (
            utils.extract(self.tempdir.name, super().path)
            if self.is_tarball
            else super().path)

    async def upload(
            self,
            artefact: pathlib.Path,
            url: str) -> Dict[str, Union[str, pathlib.Path]]:
        if artefact.name in await self.asset_names:
            return dict(
                name=artefact.name,
                url=url,
                error=self.fail(f"Asset exists already {artefact.name}"))
        async with stream.reader(artefact) as f:
            response = await self.github.post(
                url,
                data=f,
                content_type="application/octet-stream")
        errored = (
            response.get("error")
            or not response.get("state") == "uploaded")
        result = dict(
            name=artefact.name,
            url=(response["url"]
                 if not errored
                 else url))
        if errored:
            result["error"] = self.fail(
                "Something went wrong uploading "
                f"{artefact.name} -> {url}, got:\n{response}")
        return result
