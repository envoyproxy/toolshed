import pathlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiofiles
import aiohttp

from .base import AsyncStream


class Writer(AsyncStream):
    """This wraps an async file object and provides a `stream_bytes` method to
    stream an `aiohttp.ClientResponse` to the file.

    It makes use of aiohttp's stream buffering to download chunks, and then
    writes the chunks to disk asynchronously.

    This allows large file downloads to use little or no additional
    memory while downloading with aiohttp.
    """

    async def stream_bytes(self, response: aiohttp.ClientResponse) -> None:
        """Stream chunks from an `aiohttp.ClientResponse` to an async file
        object."""
        # This is kinda aiohttp specific, we can make this more generic
        # and then adapt to aiohttp if we find the need
        async for chunk in response.content.iter_chunked(self.chunk_size):
            await self.buffer.write(chunk)


@asynccontextmanager
async def writer(
        path: str | pathlib.Path,
        chunk_size: int | None = None) -> AsyncIterator[Writer]:
    async with aiofiles.open(path, "wb") as f:
        yield Writer(f, chunk_size=chunk_size)
