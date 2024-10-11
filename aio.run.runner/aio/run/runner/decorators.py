
from functools import wraps
from typing import Callable, Type


def catches(
        errors: (
            Type[BaseException]
            | tuple[Type[BaseException], ...])) -> Callable:
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
    """Method decorator to call `.cleanup()` after run.

    Can work with `sync` and `async` methods.
    """

    @wraps(fun)
    def wrapped(self, *args, **kwargs) -> int | None:
        try:
            return fun(self, *args, **kwargs)
        finally:
            self.cleanup()

    # mypy doesnt trust `@wraps` to give back a `__wrapped__` object so we
    # need to code defensively here
    wrapping = getattr(wrapped, "__wrapped__", None)
    if wrapping:
        setattr(wrapping, "__cleansup__", True)
    return wrapped
