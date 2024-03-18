
from functools import partial
from typing import Any, Callable, Optional

import abstracts

from aio.core import event, functional, tasks
from aio.core.dev import debug


# TODO: split `IReactive.pool` to here
class IExecutive(event.IReactive, metaclass=abstracts.Interface):
    """Object that executes commands in a process pool."""

    @abstracts.interfacemethod
    async def execute(
            self,
            executable: Callable,
            *args,
            **kwargs) -> Any:
        """Execute a command in a process pool."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def execute_in_batches(
            self,
            executable: Callable,
            *args,
            concurrency: Optional[int] = None,
            min_batch_size: Optional[int] = None,
            max_batch_size: Optional[int] = None,
            **kwargs) -> functional.AwaitableGenerator:
        """Execute a command in a process pool."""
        raise NotImplementedError


@abstracts.implementer((event.AReactive, IExecutive))
class AExecutive(metaclass=abstracts.Abstraction):

    @debug.logging(
        log=__name__,
        format_result="self._debug_execute")
    async def execute(
            self,
            executable: Callable,
            *args,
            **kwargs) -> Any:
        return await self.loop.run_in_executor(
            self.pool,
            *(executable, *args),
            **kwargs)

    def execute_in_batches(
            self,
            executable: Callable,
            *args,
            concurrency: Optional[int] = None,
            min_batch_size: Optional[int] = None,
            max_batch_size: Optional[int] = None,
            **kwargs) -> functional.AwaitableGenerator:
        return tasks.concurrent(
            (self.execute(
                executable,
                *batch,
                **kwargs)
             for batch
             in functional.batch_jobs(
                 args,
                 min_batch_size=min_batch_size,
                 max_batch_size=max_batch_size)),
            limit=concurrency)

    def _debug_execute(self, start, result, time_taken, result_info):
        (instance, (executable, *args), kwargs), start_time = start
        pool_name = (
            "\N{forking}"
            if self.pool.__class__.__name__ == "ProcessPoolExecutor"
            else "\N{nonforking}")
        pool_info = f"{pool_name}:{hex(id(self.pool))}"
        if type(executable) is partial:
            executable = executable.func
        name = getattr(
            executable, "__qualname__",
            executable.__class__.__qualname__)
        return (
            f"{pool_info} {result_info}: "
            f"{executable.__module__}{name}")
