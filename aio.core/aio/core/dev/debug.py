
import inspect
import logging as _logging
import time
from functools import partial
from typing import Any, Callable, Optional


logger = _logging.getLogger(__name__)


class logging:

    def __init__(self, fun: Optional[Callable] = None, *args, **kwargs):
        self._fun = fun
        self.__doc__ = getattr(fun, '__doc__')
        self._log = kwargs.pop("log", None)
        self._format_result = kwargs.pop("format_result", None)

    def __call__(self, fun: Optional[Callable] = None):
        self._fun = fun
        self.__doc__ = getattr(fun, '__doc__')
        return self

    def __get__(self, instance: Any, cls=None) -> Any:
        if instance is None:
            return self
        if inspect.isasyncgenfunction(self._fun):
            return partial(self.fun_async_gen, instance)
        elif inspect.iscoroutinefunction(self._fun):
            return partial(self.fun_async, instance)
        elif inspect.isgeneratorfunction(self._fun):
            return partial(self.fun_gen, instance)
        return partial(self.fun, instance)

    def log(self, instance):
        if self._log:
            if isinstance(self._log, str):
                if self._log.startswith("self."):
                    return getattr(instance, self._log[5:])
                return _logging.getLogger(self._log)
            return self._log
        return logger

    def format_result(self, instance):
        if not self._format_result:
            return
        if isinstance(self._format_result, str):
            if self._format_result.startswith("self."):
                return getattr(instance, self._format_result[5:])
        return self._format_result

    def fun(self, *args, **kwargs):
        return self.log_debug_complete(
            self.log_debug_start(*args, **kwargs),
            self._fun(*args, **kwargs))

    def fun_gen(self, *args, **kwargs):
        start = self.log_debug_start(*args, **kwargs)
        count = 0
        for item in self._fun(*args, **kwargs):
            count += 1
            yield item
        self.log_debug_complete_iter(start, count)

    async def fun_async(self, *args, **kwargs):
        return self.log_debug_complete(
            self.log_debug_start(*args, **kwargs),
            await self._fun(*args, **kwargs))

    async def fun_async_gen(self, *args, **kwargs):
        start = self.log_debug_start(*args, **kwargs)
        count = 0
        async for item in self._fun(*args, **kwargs):
            count += 1
            yield item
        self.log_debug_complete_iter(start, count)

    def log_debug_start(self, instance, *args, **kwargs):
        self.log(instance).debug(
            f"{self._fun.__qualname__} called\n"
            f"ARGS: {args}\n  KWARGS: {kwargs}")
        return (instance, args, kwargs), time.perf_counter()

    def log_debug_complete(self, start, result):
        (instance, args, kwargs), start_time = start
        time_taken = time.perf_counter() - start_time
        try:
            len_info = str(len(result))
        except TypeError:
            len_info = ""
        result_info = (
            f"{type(result).__name__:5} {len_info:4} "
            f"{time_taken:6.3f}s")
        formatter = self.format_result(instance)
        if formatter:
            result_info = formatter(
                start, result, time_taken, result_info)
        self.log(instance).debug(
            f"{self._fun.__qualname__} returns {result_info}")
        return result

    def log_debug_complete_iter(self, start, count):
        (instance, args, kwargs), start_time = start
        time_taken = time.perf_counter() - start_time
        result_info = (
            f"type(self._fun).__name__ {count:4} "
            f"{time_taken:6.3f}s")
        formatter = self.format_result(instance)
        if formatter:
            result_info = formatter(
                start, count, time_taken, result_info)
        self.log(instance).debug(
            f"{self._fun.__qualname__} generated {result_info}")
