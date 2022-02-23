
import logging
from typing import Any, Callable, Optional

import abstracts

from aio.core import event, functional, tasks


logger = logging.getLogger(__name__)


# TODO: split `IReactive.pool` to here
class IExecutive(event.IReactive, metaclass=abstracts.Interface):
    """Object that executes commands in a process pool."""

    @abstracts.interfacemethod
    async def execute(
            self,
            executable: Callable,
            *args,
            use_pool: bool = True,
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

    async def execute(
            self,
            executable: Callable,
            *args,
            **kwargs) -> Any:
        logger.debug(
            f"Executing: {executable}\n  {args}\n  {kwargs}")
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
