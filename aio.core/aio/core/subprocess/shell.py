
from concurrent import futures
from subprocess import CompletedProcess

import abstracts

from aio.core import functional, subprocess


@abstracts.implementer(subprocess.AAsyncShell)
class AsyncShell:

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def executor(self) -> futures.Executor:
        return super().executor

    def parallel(self, *args, **kwargs) -> "functional.AwaitableGenerator":
        return super().parallel(*args, **kwargs)

    async def run(self, *args, **kwargs) -> CompletedProcess:
        return await super().run(*args, **kwargs)
