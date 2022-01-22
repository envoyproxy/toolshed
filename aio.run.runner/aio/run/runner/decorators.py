from functools import wraps
from typing import Callable, Optional, Tuple, Type, Union


def catches(
        errors: Union[
            Type[BaseException],
            Tuple[Type[BaseException], ...]]) -> Callable:
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
        async def wrapped(self, *args, **kwargs) -> Optional[int]:
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
    """Method decorator to call `.cleanup()` after run."""

    @wraps(fun)
    async def wrapped(self, *args, **kwargs) -> Optional[int]:
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
