"""aio.core.subprocess."""

from .abstract import AAsyncSubprocessRunner
from .async_subprocess import AsyncSubprocess
from .subprocess import AsyncSubprocessRunner


run = AsyncSubprocess.run
parallel = AsyncSubprocess.parallel


__all__ = (
    "run",
    "parallel",
    "AAsyncSubprocessRunner",
    "AsyncSubprocess",
    "AsyncSubprocessRunner")
