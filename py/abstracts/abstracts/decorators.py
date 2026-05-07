from abc import abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from abstracts.implements import Implementer


type Implements = type | tuple[type, ...] | list[type] | set[type]


def implementer[T](
        implements: Implements,
) -> Callable[[type[T]], type[T]]:
    """Decorator for implementers.

    Assuming you have an abstract class `AFoo` which has a `metaclass` of
    type `Abstraction`, it can be used as follows:

    ```
    from tools.base import abstract

    @abstract.implementer(AFoo)
    class Foo:

        def bar(self):
            return "BAZ"

    ```
    """
    if not isinstance(implements, (tuple, list, set)):
        implements = (implements,)

    def wrapper(klass: type[T]) -> type[T]:
        dynamic_base: type[Any] = cast(type[Any], klass)

        class Implementation(dynamic_base, metaclass=Implementer):
            __implements__ = implements
            __doc__ = klass.__doc__

        # Make the resulting class look like the user-defined class in
        # tracebacks/repr/pickling.
        Implementation.__module__ = klass.__module__
        Implementation.__qualname__ = klass.__name__
        Implementation.__name__ = klass.__name__
        return cast(type[T], Implementation)

    return wrapper


def interfacemethod[F: Callable[..., object]](fun: F) -> F:

    @wraps(fun)  # type: ignore[misc]
    @abstractmethod
    def wrapped(*args, **kwargs):
        raise NotImplementedError

    wrapped.__isinterfacemethod__ = True  # type: ignore[attr-defined]
    return cast(F, wrapped)
