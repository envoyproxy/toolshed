
from functools import partial
from typing import (
    Any, Callable, Dict, Optional, Sequence,
    Tuple, Type)


class preload:

    def __init__(
            self,
            when: Sequence[str],
            blocks: Optional[Sequence[str]] = None,
            catches: Optional[Sequence[Type[BaseException]]] = None,
            name: Optional[str] = None,
            unless: Optional[Sequence[str]] = None) -> None:
        self._when = when
        self._blocks = blocks
        self._catches = catches
        self._fun: Optional[Callable] = None
        self._name = name
        self._unless = unless

    def __call__(self, fun: Callable, *args, **kwargs) -> "preload":
        self._fun = fun
        return self

    def __set_name__(self, cls: Type, name: str) -> None:
        self.name = name
        cls._preload_checks_data = self.get_preload_checks_data(cls)

    def __get__(self, instance: Any, cls: Optional[Type] = None) -> Any:
        if instance is None:
            return self
        return partial(self.fun, instance)

    @property
    def blocks(self) -> Tuple[str, ...]:
        return self.when + tuple(self._blocks or ())

    @property
    def catches(self) -> Tuple[Type[BaseException], ...]:
        return tuple(self._catches or ())

    @property
    def tag_name(self) -> str:
        return self._name or self.name

    @property
    def when(self) -> Tuple[str, ...]:
        return tuple(self._when)

    @property
    def unless(self) -> Tuple[str, ...]:
        return tuple(self._unless or ())

    def fun(self, instance, *args, **kwargs) -> Any:
        if self._fun:
            return self._fun(instance, *args, **kwargs)

    def get_preload_checks_data(
            self,
            cls: Type) -> Tuple[Tuple[str, Dict], ...]:
        preload_checks_data = dict(getattr(cls, "_preload_checks_data", ()))
        preload_checks_data[self.tag_name] = dict(
            name=self.tag_name,
            blocks=self.blocks,
            catches=self.catches,
            fun=self.fun,
            when=self.when,
            unless=self.unless)
        return tuple(preload_checks_data.items())
