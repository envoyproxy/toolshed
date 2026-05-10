from collections.abc import Callable
from typing import Any, Generic, TypeVar


T = TypeVar("T")


class classproperty(  # noqa: N801 - matches stdlib `@property` casing
        Generic[T]):
    """Read-only class-level property.

    Drop-in replacement for the deprecated ``@classmethod`` + ``@property``
    stacking, which was deprecated in Python 3.11 and removed in 3.13.

    Usage::

        class Foo:

            @classproperty
            def bar(cls) -> int:
                return 42

        Foo.bar  # -> 42
    """

    def __init__(self, fget: Callable[[Any], T]) -> None:
        self.fget = fget
        self.__doc__ = fget.__doc__

    def __get__(self, instance: Any, owner: type | None = None) -> T:
        return self.fget(owner)
