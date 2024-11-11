
import abc
import asyncio
import concurrent.futures
import pathlib
import shutil
import subprocess
from functools import partial
from typing import Optional, Union

import abstracts

from aio.api.bazel import exceptions


class ABazel(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            path: Union[pathlib.Path, str],
            bazel_path: Optional[Union[pathlib.Path, str]] = None,
            startup_options: list[str] | None = None) -> None:
        self._path = path
        self._bazel_path = bazel_path
        self.bazel_startup_options = startup_options or []

    @property
    @abc.abstractmethod
    def bazel_path(self) -> pathlib.Path:
        """Path to the Bazel binary."""
        path = self._bazel_path or shutil.which("bazel")
        if not path:
            raise exceptions.BazelError(
                "No path supplied, and `bazel` command not found")
        return pathlib.Path(path)

    @property
    @abc.abstractmethod
    def path(self) -> pathlib.Path:
        """Path to the Bazel workspace."""
        return pathlib.Path(self._path)


class ABazelCommand(ABazel):

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
        return subprocess.run(*args, **kwargs)
