
import asyncio
import concurrent.futures
import subprocess
from functools import partial

import abstracts

from aio.core.subprocess import exceptions


class AAsyncSubprocessRunner(metaclass=abstracts.Abstraction):
    """Execute a shell command asynchronously."""

    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)

    async def __call__(self, *args, **kwargs) -> subprocess.CompletedProcess:
        return await self.run(*args, **kwargs)

    async def run(
            self,
            *args,
            raises: bool = True,
            **kwargs) -> subprocess.CompletedProcess:
        """Run a bazel target and return the subprocess response."""
        run_kwargs = self.kwargs.copy()
        run_kwargs.update(kwargs)
        resp = await self.subproc_run(
            *args,
            **run_kwargs)
        if resp.returncode and raises:
            raise exceptions.RunError(f"Run failed: {resp}")
        return resp

    @property
    def executor(self) -> concurrent.futures.Executor:
        return concurrent.futures.ThreadPoolExecutor()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_running_loop()

    async def subproc_run(
            self,
            *args,
            **kwargs) -> subprocess.CompletedProcess:
        with self.executor as pool:
            return await self._run_in_executor(pool, *args, **kwargs)

    async def _run_in_executor(
            self,
            pool: concurrent.futures.Executor,
            *args,
            **kwargs) -> subprocess.CompletedProcess:
        return await self.loop.run_in_executor(
            pool,
            partial(self._subproc_run, *args, **kwargs))

    def _subproc_run(
            self,
            *args,
            **kwargs) -> subprocess.CompletedProcess:
        """Fork a subprocess, using self.context.path as the cwd by default."""
        kwargs["cwd"] = kwargs.pop("cwd", None) or self.path
        kwargs["capture_output"] = kwargs.pop("capture_output", True)
        # joined_args = " ".join(args[0])
        # print(f"RUN: {joined_args}")
        result = subprocess.run(*args, **kwargs)
        return result
