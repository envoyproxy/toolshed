
from typing import Any

import abstracts

from aio.core import event


# TODO: split `IReactive.pool` to here
class IExecutive(event.IReactive, metaclass=abstracts.Interface):
    """Object that executes commands in a process pool."""

    @abstracts.interfacemethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute a command in a process pool."""
        raise NotImplementedError


@abstracts.implementer((event.AReactive, IExecutive))
class AExecutive(metaclass=abstracts.Abstraction):

    async def execute(self, *args, **kwargs) -> Any:
        return await self.loop.run_in_executor(
            self.pool,
            *args,
            **kwargs)
