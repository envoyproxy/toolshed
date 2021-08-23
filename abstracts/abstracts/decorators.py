from abc import abstractmethod
from functools import wraps
from typing import Any

from abstracts.implements import Implementer


def implementer(implements):
    """Decorator for implementers

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
        # This is a v annoying workaround for mypy, see:
        #   https://github.com/python/mypy/issues/9183
        _klass: Any = klass

        class Implementation(_klass, metaclass=Implementer):
            __implements__ = implements
            __doc__ = _klass.__doc__

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
