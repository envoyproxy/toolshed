
from concurrent import futures
from subprocess import CompletedProcess
from typing import AsyncIterator

import abstracts

from aio.core import subprocess


@abstracts.implementer(subprocess.AAsyncShell)
class AsyncShell:

    @property
    def executor(self) -> futures.Executor:
        return super().executor

    def parallel(self, *args, **kwargs) -> AsyncIterator:
        return super().parallel(*args, **kwargs)

    async def run(self, *args, **kwargs) -> CompletedProcess:
        return await super().run(*args, **kwargs)
