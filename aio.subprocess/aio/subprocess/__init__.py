"""aio.subprocess."""

from aio.subprocess.async_subprocess import AsyncSubprocess


run = AsyncSubprocess.run
parallel = AsyncSubprocess.parallel


__all__ = ("run", "parallel", "AsyncSubprocess")
