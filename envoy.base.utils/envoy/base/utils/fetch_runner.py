
import asyncio
import json
import hashlib
import os
import pathlib
import time
from functools import cached_property
from typing import Optional
from urllib.parse import urlsplit

import aiohttp

from aio.core.tasks import concurrent
from aio.run import runner

from envoy.base import utils


DEFAULT_CHUNK_SIZE = 32768
DEFAULT_MAX_CONCURRENCY = 3


class FetchRunner(runner.Runner):

    @cached_property
    def downloads(self) -> dict[str, dict]:
        return json.load(pathlib.Path(self.args.downloads).open())

    @cached_property
    def downloads_path(self) -> pathlib.Path:
        return pathlib.Path(self.tempdir.name).joinpath("downloads")

    @cached_property
    def excludes(self) -> list[str]:
        return (
            pathlib.Path(self.args.excludes).read_text().splitlines()
            if self.args.excludes
            else [])

    @property
    def headers(self) -> dict:
        return (
            {}
            if not self.token
            else dict(
                Authorization=f"token {self.token}",
                Accept="application/octet-stream"))

    @property
    def time_elapsed(self) -> float:
        start = self.time_start
        return round(time.time() - start, 3)

    @cached_property
    def time_start(self) -> float:
        return time.time()

    @property
    def token(self) -> Optional[str]:
        """Github access token."""
        if self.args.token_path:
            return pathlib.Path(self.args.token_path).read_text().strip()
        elif self.args.token:
            return os.getenv(self.args.token)

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return aiohttp.ClientSession()

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument("downloads", help="JSON k/v of downloads/info")
        parser.add_argument(
            "--chunk-size",
            default=DEFAULT_CHUNK_SIZE,
            type=int,
            help="Download chunk size")
        parser.add_argument(
            "--concurrency",
            default=DEFAULT_MAX_CONCURRENCY,
            type=int,
            help="Maximum concurrent downloads")
        parser.add_argument(
            "--excludes",
            help="Path to file containing newline separated paths to exclude")
        parser.add_argument(
            "--extract-downloads",
            action="store_true",
            default=False,
            help="Extract downloaded files")
        parser.add_argument(
            "--output",
            help="Output format")
        parser.add_argument(
            "--output-path",
            help="Output path")
        parser.add_argument(
            "--token",
            help="Env name for auth token")
        parser.add_argument(
            "--token-path",
            help="Path to auth token")

    def download_path(self, url: str) -> Optional[pathlib.Path]:
        if "path" not in self.downloads[url]:
            return None
        return self.downloads_path.joinpath(
            self.downloads[url]["path"],
            self.filename(url))

    def excluded(self, url: str) -> bool:
        path = self.downloads[url].get("path")
        return bool(path and path in self.excludes)

    async def fetch(self, url: str) -> tuple[str, Optional[bytes]]:
        self.log.debug(
            f"{self.time_elapsed} Fetching:\n"
            f" {url}\n")
        download_path = self.download_path(url)
        if download_path:
            download_path.parent.mkdir(parents=True, exist_ok=True)
        return await self.fetch_bytes(url, path=download_path)

    async def fetch_bytes(
            self,
            url: str,
            path: Optional[pathlib.Path] = None) -> (
                tuple[str, Optional[bytes]]):
        async with self.session.get(url, headers=self.headers) as response:
            response.raise_for_status()
            if not path:
                return url, await response.read()

            self.log.debug(
                f"{self.time_elapsed} "
                f"Writing chunks({self.args.chunk_size}):\n"
                f" {url}\n"
                f" -> {path}")
            with path.open("wb") as f:
                chunks = response.content.iter_chunked(self.args.chunk_size)
                async for chunk in chunks:
                    f.write(chunk)

            if "checksum" in self.downloads[url]:
                await self.validate_checksum(url)

            if self.args.extract_downloads:
                await asyncio.to_thread(utils.extract, path.parent, path)
                path.unlink()

            return url, None

    def filename(self, url: str) -> str:
        parsed_url = urlsplit(url)
        path_parts = parsed_url.path.split("/")
        return path_parts[-1]

    def hashed(self, content: bytes) -> str:
        hash_object = hashlib.sha256()
        hash_object.update(content)
        return hash_object.hexdigest()

    @runner.cleansup
    async def run(self) -> Optional[int]:
        result = {}
        downloads = concurrent(
            (self.fetch(url)
             for url
             in self.downloads
             if not self.excluded(url)),
            limit=self.args.concurrency)

        async for (url, response) in downloads:
            self.log.debug(
                f"{self.time_elapsed} "
                f"Received:\n"
                f" {url}\n")
            if self.args.output == "json":
                result[url] = response.decode()

        if self.args.output == "json":
            print(json.dumps(result))
            return 0

        if not self.args.output_path:
            return 0
        self.log.debug(
            f"{self.time_elapsed} "
            f"Packing:\n"
            f" {self.downloads_path}\n"
            f" {self.args.output_path}\n")
        await asyncio.to_thread(
            utils.pack,
            self.downloads_path,
            self.args.output_path)

    async def cleanup(self):
        await super().cleanup()
        await self.session.close()

    async def validate_checksum(self, url: str) -> None:
        path = self.download_path(url)
        if not path:
            return
        hashed = await asyncio.to_thread(
            self.hashed,
            path.read_bytes())
        checksum = self.downloads[url]["checksum"]
        self.log.debug(
            f"{self.time_elapsed} "
            f"Validating:\n"
            f" {url}\n"
            f" {checksum}\n")
        if hashed != checksum:
            raise utils.exceptions.ChecksumError(
                f"Checksums do not match({url}):\n"
                f" expected: {checksum}\n"
                f" received: {hashed}")