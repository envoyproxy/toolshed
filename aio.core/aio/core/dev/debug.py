
import inspect
import logging as _logging
import os
import time
from functools import cached_property, partial
from typing import Any, Callable, Optional

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore


logger = _logging.getLogger(__name__)

if not psutil:
    logger.warning(
        "Unable to import `psutil`. Most likely related to: "
        "https://github.com/bazelbuild/rules_python/issues/622")


class ADebugLogging:

    def __init__(self, fun: Optional[Callable] = None, *args, **kwargs):
        self.__wrapped__ = fun
        self.__doc__ = getattr(fun, '__doc__')
        self._log = kwargs.pop("log", None)
        self._format_result = kwargs.pop("format_result", None)
        self._show_cpu = kwargs.pop("show_cpu", None)

    def __call__(self, *args, **kwargs):
        if self.__wrapped__:
            if inspect.isasyncgenfunction(self.__wrapped__):
                return self.fun_async_gen(*args, **kwargs)
            elif inspect.iscoroutinefunction(self.__wrapped__):
                return self.fun_async(*args, **kwargs)
            elif inspect.isgeneratorfunction(self.__wrapped__):
                return self.fun_gen(*args, **kwargs)
            return self.fun(*args, **kwargs)
        fun: Optional[Callable] = args[0] if args else None
        self.__wrapped__ = fun
        self.__doc__ = getattr(fun, '__doc__')
        return self

    def __get__(self, instance: Any, cls=None) -> Any:
        if instance is None:
            return self
        if inspect.isasyncgenfunction(self.__wrapped__):
            return partial(self.fun_async_gen, instance)
        elif inspect.iscoroutinefunction(self.__wrapped__):
            return partial(self.fun_async, instance)
        elif inspect.isgeneratorfunction(self.__wrapped__):
            return partial(self.fun_gen, instance)
        return partial(self.fun, instance)

    @cached_property
    def name(self) -> str:
        return (
            getattr(
                self.__wrapped__, "__qualname__", None)
            or getattr(
                self.__wrapped__, "__name__", None)
            or self.__class__.__name__)

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
            self.__wrapped__(*args, **kwargs))

    def fun_gen(self, *args, **kwargs):
        start = self.log_debug_start(*args, **kwargs)
        count = 0
        for item in self.__wrapped__(*args, **kwargs):
            count += 1
            yield item
        self.log_debug_complete_iter(start, count)

    async def fun_async(self, *args, **kwargs):
        return self.log_debug_complete(
            self.log_debug_start(*args, **kwargs),
            await self.__wrapped__(*args, **kwargs))

    async def fun_async_gen(self, *args, **kwargs):
        start = self.log_debug_start(*args, **kwargs)
        count = 0
        async for item in self.__wrapped__(*args, **kwargs):
            count += 1
            yield item
        self.log_debug_complete_iter(start, count)

    def log_debug_start(self, instance, *args, **kwargs):
        self.log(instance).debug(
            f"{self.name} called "
            f"(args: {len(args)}, kwargs: {len(kwargs)})")
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
            f"{self.name}{self._cpu_info} returns {result_info}")
        return result

    def log_debug_complete_iter(self, start, count):
        (instance, args, kwargs), start_time = start
        time_taken = time.perf_counter() - start_time
        cpu_info = (
            f"(cpu: {psutil.Process(os.getpid()).cpu_num()}) "
            if self._show_cpu
            else "")
        result_info = (
            f"{type(self.__wrapped__).__name__:5} {count:4} "
            f"{time_taken:6.3f}s")
        formatter = self.format_result(instance)
        if formatter:
            result_info = formatter(
                start, count, time_taken, result_info)
        self.log(instance).debug(
            f"{self.name}{cpu_info}"
            f"generated {result_info}")

    @property
    def cpu_info(self):
        return (
            f" (cpu: {psutil.Process(os.getpid()).cpu_num()})"
            if psutil and self._show_cpu
            else "")


class ATraceLogging(ADebugLogging):

    def log_debug_start(self, instance, *args, **kwargs):
        start = super().log_debug_start(instance, *args, **kwargs)
        if args:
            self.log(instance).debug(
                f"{self.name} call_args\n"
                f"   {args}")
        if kwargs:
            self.log(instance).debug(
                f"{self.name} call_kwargs\n"
                f"   {kwargs}")
        return start

    def log_debug_complete(self, start, result):
        result = super().log_debug_complete(start, result)
        (instance, args, kwargs), start_time = start
        self.log(instance).debug(
            f"{self.name} return_value\n"
            f"  {result}")
        return result


class ANullLogging(ADebugLogging):

    def log_debug_start(self, instance, *args, **kwargs):
        return (instance, args, kwargs), None

    def log_debug_complete(self, start, result):
        return result

    def log_debug_complete_iter(self, start, count):
        pass


def logging(*args, **kwargs):
    if os.environ.get("AIOTRACEDEBUG"):
        return ATraceLogging(*args, **kwargs)
    if os.environ.get("AIODEBUG"):
        return ADebugLogging(*args, **kwargs)
    return ANullLogging(*args, **kwargs)
