
import abc
import asyncio
from functools import partial
from typing import Any, Generator, Optional, Tuple

import abstracts


class AAsyncWrapper(metaclass=abstracts.Abstraction):
    _loop = None

    def __init__(
            self,
            context: object,
            loop: Optional[asyncio.AbstractEventLoop] = None):
        self.context = context
        self._loop = loop or self._loop

    @classmethod
    def __sync_methods__(cls) -> Tuple[str, ...]:
        return ()

    @classmethod
    def __loop__(cls) -> asyncio.AbstractEventLoop:
        return cls._loop or asyncio.get_running_loop()

    @classmethod
    @abc.abstractmethod
    def __async_methods__(cls, context: object) -> Generator:
        for k in dir(context):
            if k.startswith("_") or k in cls.__sync_methods__():
                continue
            if callable(getattr(context, k)):
                yield k

    @classmethod
    async def async_exec(cls, *args, **kwargs) -> Any:
        return await cls.__loop__().run_in_executor(
            None, *args, **kwargs)

    def __new__(cls, context: object, loop=None) -> "AAsyncWrapper":
        klass: Any = cls

        class Wrapped(klass):
            _loop = loop

        async def wrapper(method: str, *args, **kwargs) -> Any:
            return await cls.async_exec(
                getattr(context, method),
                *args,
                **kwargs)

        for k in cls.__async_methods__(context):
            fun = partial(wrapper, k)
            # fun.__name__ = k
            setattr(Wrapped, k, fun)

        Wrapped.__qualname__ = f"{cls.__name__}"
        return super().__new__(Wrapped)
