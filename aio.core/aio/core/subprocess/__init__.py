"""aio.core.subprocess."""

from .async_subprocess import AsyncSubprocess, run, parallel
from .abstract import AAsyncShell
from .handler import ASubprocessHandler, ISubprocessHandler
from .shell import AsyncShell


__all__ = (
    "run",
    "parallel",
    "AAsyncShell",
    "ASubprocessHandler",
    "AsyncSubprocess",
    "AsyncShell",
    "ISubprocessHandler")
