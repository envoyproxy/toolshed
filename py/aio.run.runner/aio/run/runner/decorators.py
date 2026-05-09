
from collections.abc import Callable
from functools import wraps


def catches(
        errors: (
            type[BaseException]
            | tuple[type[BaseException], ...])) -> Callable:
    """Method decorator to catch specified errors.

    logs and returns 1 for sys.exit if error/s are caught

    can be used as so:

    ```python

    class MyRunner(runner.Runner):

        @runner.catches((MyError, MyOtherError))
        async def run(self):
            self.myrun()
    ```
    """

    def wrapper(fun: Callable) -> Callable:

        @wraps(fun)
        async def wrapped(self, *args, **kwargs) -> int | None:
            try:
                return await fun(self, *args, **kwargs)
            except errors as e:
                self.log.error(str(e) or repr(e))
                return 1

        # mypy doesnt trust `@wraps` to give back a `__wrapped__` object so we
        # need to code defensively here
        wrapping = getattr(wrapped, "__wrapped__", None)
        if wrapping:
            setattr(wrapping, "__catches__", errors)
        return wrapped

    return wrapper


def cleansup(fun) -> Callable:
    """Async method decorator to call `await self.cleanup()` after run.

    Wraps an `async` method so that `await self.cleanup()` is always
    invoked in a `finally` block, regardless of whether the wrapped
    method returns normally or raises.

    Only `async` methods are supported.

    Example:

    ```python

    class MyRunner(runner.Runner):

        @runner.cleansup
        async def run(self):
            ...
    ```
    """

    @wraps(fun)
    async def wrapped(self, *args, **kwargs) -> int | None:
        try:
            return await fun(self, *args, **kwargs)
        finally:
            await self.cleanup()

    # mypy doesnt trust `@wraps` to give back a `__wrapped__` object so we
    # need to code defensively here
    wrapping = getattr(wrapped, "__wrapped__", None)
    if wrapping:
        setattr(wrapping, "__cleansup__", True)
    return wrapped
