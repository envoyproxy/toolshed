
import asyncio
from functools import cached_property
from typing import Any, Generator

import abstracts


class ILoader(metaclass=abstracts.Interface):
    """Maintains loading/loaded state and allows you to wait for those events
    to complete.

    Allows multiple, potentially concurrent, tasks to wait on a shared
    resource, triggering its loading only if required.

    ```python

    loader = Loader()
    data = None

    def task():
        # If the loader is loading it will wait until it completes otherwise
        # it returns immediately. The return value is the "loaded" state.
        if not await loader:
           # Loader hasnt been loaded yet
            with loader:
                data = await some_slow_task()

    asyncio.create_task(task())

    ```

    later...

    ```python

    if not await loader:
        with loader:
            data = await some_slow_task()
    ```
    """

    @abstracts.interfacemethod
    def __await__(self) -> Generator[Any, None, bool]:
        """Wait for the loader *if* it is already loading, finally returning
        "loaded" state."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def __enter__(self) -> None:
        """Start loading within a context."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def __exit__(self, *exception) -> None:
        """Complete loading exiting the context."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def loaded(self) -> bool:
        """Flag to indicate "loaded" state."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def loading(self) -> bool:
        """Flag to indicate "loading" state."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def complete(self) -> None:
        """Complete loading."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def start(self) -> None:
        """Start loading."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def wait(self) -> bool:
        """Wait for the loader *if* it is already loading, finally returning
        "loaded" state."""
        raise NotImplementedError


@abstracts.implementer(ILoader)
class ALoader(metaclass=abstracts.Abstraction):

    def __await__(self) -> Generator[Any, None, bool]:
        return self.wait().__await__()

    def __enter__(self) -> None:
        self.start()

    def __exit__(self, *exception) -> None:
        self.complete()

    @property
    def loaded(self) -> bool:
        return self._loaded.is_set()

    @property
    def loading(self) -> bool:
        return self._loading.is_set()

    def start(self) -> None:
        self._loading.set()

    def complete(self) -> None:

        self._loading.clear()
        self._loaded.set()

    @cached_property
    def _loaded(self) -> asyncio.Event:
        return asyncio.Event()

    @cached_property
    def _loading(self) -> asyncio.Event:
        return asyncio.Event()

    async def wait(self) -> bool:
        if self.loading:
            await self._loaded.wait()
        return self.loaded


@abstracts.implementer(ILoader)
class Loader(ALoader):
    pass
