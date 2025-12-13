
from functools import partial
from typing import (
    Any, Callable, Sequence, Type)


class preload:

    def __init__(
            self,
            when: Sequence[str],
            blocks: Sequence[str] | None = None,
            catches: Sequence[Type[BaseException]] | None = None,
            name: str | None = None,
            unless: Sequence[str] | None = None) -> None:
        self._when = when
        self._blocks = blocks
        self._catches = catches
        self._fun: Callable | None = None
        self._name = name
        self._unless = unless

    def __call__(self, fun: Callable, *args, **kwargs) -> "preload":
        self._fun = fun
        return self

    def __set_name__(self, cls: Type, name: str) -> None:
        self.name = name
        cls._preload_checks_data = self.get_preload_checks_data(cls)

    def __get__(self, instance: Any, cls: Type | None = None) -> Any:
        if instance is None:
            return self
        return partial(self.fun, instance)

    @property
    def blocks(self) -> tuple[str, ...]:
        return self.when + tuple(self._blocks or ())

    @property
    def catches(self) -> tuple[Type[BaseException], ...]:
        return tuple(self._catches or ())

    @property
    def tag_name(self) -> str:
        return self._name or self.name

    @property
    def when(self) -> tuple[str, ...]:
        return tuple(self._when)

    @property
    def unless(self) -> tuple[str, ...]:
        return tuple(self._unless or ())

    def fun(self, instance, *args, **kwargs) -> Any:
        if self._fun:
            return self._fun(instance, *args, **kwargs)

    def get_preload_checks_data(
            self,
            cls: Type) -> tuple[tuple[str, dict], ...]:
        preload_checks_data = dict(getattr(cls, "_preload_checks_data", ()))
        preload_checks_data[self.tag_name] = dict(
            name=self.tag_name,
            blocks=self.blocks,
            catches=self.catches,
            fun=self.fun,
            when=self.when,
            unless=self.unless)
        return tuple(preload_checks_data.items())
