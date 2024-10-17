import pathlib
from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator, Optional, Union

import aiofiles
from aiofiles.threadpool.binary import AsyncBufferedReader

from .base import AsyncStream


class Reader(AsyncStream):
    """This wraps an `AsyncBufferedReader` with a `__len__`

    This is useful if you want to a pass an `AsyncBufferedReader`
    as the body data to an `HTTP` stream, but the `HTTP` client
    wants to send a `Content-Length` header, based on the `len()`
    of the data.

    As the file's size can be gleaned from the OS `stat_size`,
    this can be set ahead of reading chunks from the file.

    This allows large file uploads to use little or no additional
    memory while uploading with aiohttp.
    """

    def __init__(self, *args, size: Optional[int] = None, **kwargs):
        self._size = size
        super().__init__(*args, **kwargs)

    async def __aiter__(self) -> AsyncGenerator[bytes, AsyncBufferedReader]:
        while True:
            if not (chunk := await self.buffer.read(self.chunk_size)):
                break
            yield chunk

    def __len__(self) -> int:
        if self.size is None:
            raise TypeError(
                f"object of type '{self.__class__.__name__}' with no 'size' "
                "cannot get len()")
        return self.size

    @property
    def size(self) -> Optional[int]:
        return self._size


@asynccontextmanager
async def reader(
        path: Union[str, pathlib.Path],
        chunk_size: Optional[int] = None) -> AsyncIterator[Reader]:
    path = pathlib.Path(path)
    async with aiofiles.open(path, "rb") as f:
        yield Reader(f, chunk_size=chunk_size, size=path.stat().st_size)
