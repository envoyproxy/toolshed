
import asyncio
import json
import hashlib
import io
import os
import pathlib
import time
from functools import cached_property
from typing import IO
from urllib.parse import urlsplit

import aiohttp

import gnupg  # type:ignore

from aio.core.tasks import concurrent, ConcurrentExecutionError
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

    @cached_property
    def gpg(self) -> gnupg.GPG:
        return gnupg.GPG()

    @property
    def headers(self) -> dict:
        return (
            {}
            if not self.token
            else dict(
                Authorization=f"token {self.token}",
                Accept="application/octet-stream"))

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return aiohttp.ClientSession()

    @property
    def time_elapsed(self) -> float:
        start = self.time_start
        return round(time.time() - start, 3)

    @cached_property
    def time_start(self) -> float:
        return time.time()

    @property
    def token(self) -> str | None:
        """Github access token."""
        if self.args.token_path:
            return pathlib.Path(self.args.token_path).read_text().strip()
        elif self.args.token:
            return os.getenv(self.args.token)

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

    async def cleanup(self):
        await super().cleanup()
        await self.session.close()

    def download_path(
            self, url: str,
            create: bool = True) -> pathlib.Path | None:
        if "path" not in self.downloads[url]:
            return None
        _download_path = self.downloads_path.joinpath(
            self.downloads[url]["path"],
            self.filename(url))
        if create:
            _download_path.parent.mkdir(parents=True, exist_ok=True)
        return _download_path

    def excluded(self, url: str) -> bool:
        path = self.downloads[url].get("path")
        return bool(path and path in self.excludes)

    async def fetch(self, url: str) -> tuple[str, bytes]:
        self.log.debug(
            f"{self.time_elapsed} Fetching:\n"
            f" {url}\n")
        download_path = self.download_path(url)
        buffer: IO[bytes] = (
            download_path.open("wb+")
            if download_path
            else io.BytesIO())
        with buffer as fd:
            await self.fetch_bytes(url, fd)
            await self.validate(url, fd)
            content: bytes = (
                fd.read()
                if not download_path
                else b'')
        if download_path and self.args.extract_downloads:
            await asyncio.to_thread(
                utils.extract,
                download_path.parent,
                download_path)
            download_path.unlink()
        return url, content

    async def fetch_bytes(
            self,
            url: str,
            fd: IO[bytes]) -> None:
        dest = (
            f" -> {fd.name}"
            if hasattr(fd, "name")
            else "")
        async with self.session.get(url, headers=self.headers) as response:
            response.raise_for_status()
            self.log.debug(
                f"{self.time_elapsed} "
                f"Writing chunks({self.args.chunk_size}):\n"
                f" {url}\n"
                f"{dest}")
            chunks = response.content.iter_chunked(self.args.chunk_size)
            async for chunk in chunks:
                fd.write(chunk)

    def filename(self, url: str) -> str:
        parsed_url = urlsplit(url)
        path_parts = parsed_url.path.split("/")
        return path_parts[-1]

    def hashed(self, fd: IO[bytes]) -> str:
        hash_object = hashlib.sha256()
        hash_object.update(fd.read())
        return hash_object.hexdigest()

    @runner.cleansup
    @runner.catches(
        (utils.exceptions.SignatureError,
         ConcurrentExecutionError))
    async def run(self) -> int | None:
        result = {}
        downloads = concurrent(
            (self.fetch(url)
             for url
             in self.downloads
             if not self.excluded(url)),
            limit=self.args.concurrency)

        async for (url, content) in downloads:
            self.log.debug(
                f"{self.time_elapsed} "
                f"Received:\n"
                f" {url}\n")
            if self.args.output == "json":
                result[url] = content.decode()

        if self.args.output == "json":
            print(json.dumps(result))
            return 0
        exit_now = (
            not self.args.output_path
            or not self.downloads_path.exists()
            or not any(self.downloads_path.iterdir()))
        if exit_now:
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

    async def validate(
            self,
            url: str,
            fd: IO[bytes]) -> None:
        # These cant be run in parallel without passing
        # the data rather than a buffer/file descriptor.
        if "signature" in self.downloads[url]:
            fd.seek(0)
            await self.validate_signature(url, fd)
        if "checksum" in self.downloads[url]:
            fd.seek(0)
            await self.validate_checksum(url, fd)
        fd.seek(0)

    async def validate_checksum(
            self,
            url: str,
            fd: IO[bytes]) -> None:
        checksum = self.downloads[url]["checksum"]
        hashed = await asyncio.to_thread(
            self.hashed,
            fd)
        self.log.debug(
            f"{self.time_elapsed} "
            f"Validating checksum:\n"
            f" {url}\n"
            f" {checksum}\n")
        if hashed != checksum:
            raise utils.exceptions.ChecksumError(
                f"Checksums do not match({url}):\n"
                f" expected: {checksum}\n"
                f" received: {hashed}")

    async def validate_signature(
            self,
            url: str,
            fd: IO[bytes]) -> None:
        digest = self.gpg.verify_file(fd)
        signature = self.downloads[url]["signature"]
        self.log.debug(
            f"{self.time_elapsed} "
            f"Validating signature:\n"
            f" {url}\n"
            f" {signature}\n")
        if not digest.valid:
            problems = "\n ".join(str(p) for p in digest.problems)
            raise utils.exceptions.SignatureError(
                f"Signature not valid:\n"
                f" {url}\n"
                f" {problems}")
        if not digest.username == signature:
            raise utils.exceptions.SignatureError(
                f"Signature not correct:\n"
                f" expected: {signature}\n"
                f" received: {digest.username}")
