#
# Decorators
#

import inspect
import logging
from functools import cached_property
from typing import Any, Callable, Dict, Optional

from aio.core import event
from aio.core.dev import debug


logger = logging.getLogger(__name__)


class NoCache(Exception):
    pass


class async_property:  # noqa: N801
    name = None
    cache_name = "__async_prop_cache__"

    @classmethod
    def is_cached(cls, item: object, name: str) -> bool:
        return (
            hasattr(item, cls.cache_name)
            and name in getattr(item, cls.cache_name))

    # If the decorator is called with `kwargs` then `fun` is `None`
    # and instead `__call__` is triggered with `fun`
    def __init__(self, fun: Optional[Callable] = None, cache: bool = False):
        self.cache = cache
        self._fun = fun
        self.name = getattr(fun, "__name__", None)
        self.__doc__ = getattr(fun, '__doc__')
        if fun and hasattr(fun, "__isabstractmethod__"):
            self.__isabstractmethod__ = fun.__isabstractmethod__  # type:ignore
        if fun and hasattr(fun, "__isinterfacemethod__"):
            self.__isinterfacemethod__ = (
                fun.__isinterfacemethod__)  # type:ignore

    def __call__(self, fun: Callable) -> 'async_property':
        self._fun = fun
        self.name = self.name or fun.__name__
        self.__doc__ = getattr(fun, '__doc__')
        if hasattr(fun, "__isabstractmethod__"):
            self.__isabstractmethod__ = fun.__isabstractmethod__  # type:ignore
        if hasattr(fun, "__isinterfacemethod__"):
            self.__isinterfacemethod__ = (
                fun.__isinterfacemethod__)  # type:ignore
        return self

    def __get__(self, instance: Any, cls=None) -> Any:
        if instance is None:
            return self
        if inspect.isasyncgenfunction(self._fun):
            return self.async_iter_result(instance)
        return self.async_result(instance)

    @cached_property
    def loaders(self) -> Dict[str, event.Loader]:
        return {}

    def fun(self, *args, **kwargs):
        if self._fun:
            return self._fun(*args, **kwargs)

    def get_prop_cache(self, instance: Any) -> dict:
        return getattr(instance, self.cache_name, {})

    # An async wrapper function to return the result
    # This is returned when the prop is called if the wrapped
    # method is an async generator
    async def async_iter_result(self, instance: Any):
        # retrieve the value from cache if available
        try:
            result = self.get_cached_prop(instance)
        except (NoCache, KeyError):
            result = None

        if result is None:
            result = self.set_prop_cache(instance, self.fun(instance))

        async for item in result:
            yield item

    # An async wrapper function to return the result
    # This is returned when the prop is called
    async def async_result(self, instance: Any) -> Any:
        # retrieve the value from cache if available
        try:
            return self.get_cached_prop(instance)
        except (NoCache, KeyError):
            pass
        if self.cache:
            return await self.load_cooperatively(instance)
        return await self.load(instance)

    def get_cached_prop(self, instance: Any) -> Any:
        if not self.cache:
            raise NoCache
        return self.get_prop_cache(instance)[self.name]

    def get_loader(self, instance: Any) -> Optional[event.Loader]:
        try:
            hash(instance)
        except TypeError:
            return None
        if instance not in self.loaders:
            self.loaders[instance] = event.Loader()
        return self.loaders[instance]

    @debug.logging(
        log=__name__,
        format_result="self._debug_prop")
    async def load(self, instance: Any) -> Any:
        # derive the result, set the cache if required, and return the result
        return self.set_prop_cache(instance, await self.fun(instance))

    async def load_cooperatively(self, instance: Any) -> Any:
        loader = self.get_loader(instance)
        if not loader:
            # Unhashable type, just load
            return await self.load(instance)
        if not await loader:
            with loader:
                return await self.load(instance)
        return self.get_cached_prop(instance)

    def set_prop_cache(self, instance: Any, result: Any) -> Any:
        if not self.cache:
            return result
        cache = self.get_prop_cache(instance)
        cache[self.name] = result
        setattr(instance, self.cache_name, cache)
        return result

    def _debug_prop(self, start, result, time_taken, result_info):
        (instance, args, kwargs), start_time = start
        cache = (
            "\N{viewdata square}"
            if self.cache
            else "~")
        return f"{cache} {result_info}: {self._repr(instance)}"

    def _repr(self, instance: Any) -> str:
        if self._fun is None:
            return "async_property"
        return (
            f"<{instance.__class__.__module__}"
            f".{self._fun.__qualname__} {hex(id(instance))}>")
