import inspect
from functools import wraps
from typing import Callable, Optional, Tuple, Type, Union


def catches(
        errors: Union[
            Type[BaseException],
            Tuple[Type[BaseException], ...]]) -> Callable:
    """Method decorator to catch specified errors

    logs and returns 1 for sys.exit if error/s are caught

    can be used as so:

    ```python

    class MyRunner(runner.Runner):

        @runner.catches((MyError, MyOtherError))
        def run(self):
            self.myrun()
    ```

    Can work with `async` methods too.
    """

    def wrapper(fun: Callable) -> Callable:

        @wraps(fun)
        def wrapped(self, *args, **kwargs) -> Optional[int]:
            try:
                return fun(self, *args, **kwargs)
            except errors as e:
                self.log.error(str(e) or repr(e))
                return 1

        @wraps(fun)
        async def async_wrapped(self, *args, **kwargs) -> Optional[int]:
            try:
                return await fun(self, *args, **kwargs)
            except errors as e:
                self.log.error(str(e) or repr(e))
                return 1

        wrapped_fun = (
            async_wrapped
            if inspect.iscoroutinefunction(fun)
            else wrapped)

        # mypy doesnt trust `@wraps` to give back a `__wrapped__` object so we
        # need to code defensively here
        wrapping = getattr(wrapped_fun, "__wrapped__", None)
        if wrapping:
            setattr(wrapping, "__catches__", errors)
        return wrapped_fun

    return wrapper


def cleansup(fun) -> Callable:
    """Method decorator to call `.cleanup()` after run.

    Can work with `sync` and `async` methods.
    """

    @wraps(fun)
    def wrapped(self, *args, **kwargs) -> Optional[int]:
        try:
            return fun(self, *args, **kwargs)
        finally:
            self.cleanup()

    @wraps(fun)
    async def async_wrapped(self, *args, **kwargs) -> Optional[int]:
        try:
            return await fun(self, *args, **kwargs)
        finally:
            await self.cleanup()

    # mypy doesnt trust `@wraps` to give back a `__wrapped__` object so we
    # need to code defensively here
    wrapped_fun = (
        async_wrapped
        if inspect.iscoroutinefunction(fun)
        else wrapped)
    wrapping = getattr(wrapped_fun, "__wrapped__", None)
    if wrapping:
        setattr(wrapping, "__cleansup__", True)
    return wrapped_fun
