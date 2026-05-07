from abc import abstractmethod
from functools import wraps
from typing import Any

from abstracts.implements import Implementer


type Implements = type | tuple[type, ...] | list[type] | set[type]


def implementer(implements: Implements):
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

    def wrapper(klass: Any) -> Implementer:
        class Implementation(klass, metaclass=Implementer):
            __implements__ = implements
            __doc__ = klass.__doc__

        # Make the resulting class look like the user-defined class in
        # tracebacks/repr/pickling.
        Implementation.__module__ = klass.__module__
        Implementation.__qualname__ = klass.__name__
        Implementation.__name__ = klass.__name__
        return Implementation

    return wrapper


def interfacemethod(fun):

    @wraps(fun)
    @abstractmethod
    def wrapped(*args, **kwargs):
        raise NotImplementedError

    wrapped.__isinterfacemethod__ = True
    return wrapped
