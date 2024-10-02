
from typing import Optional

from aiofiles.threadpool.binary import AsyncBufferedIOBase


class AsyncStream:
    # 16k seems to offer a good balance of performance/speed
    default_chunk_size: int = 1024 * 16

    def __init__(
            self,
            buffer: AsyncBufferedIOBase,
            chunk_size: Optional[int] = None):
        self._buffer = buffer
        self._chunk_size = chunk_size

    @property
    def buffer(self) -> AsyncBufferedIOBase:
        return self._buffer

    @property
    def chunk_size(self) -> int:
        return self._chunk_size or self.default_chunk_size
