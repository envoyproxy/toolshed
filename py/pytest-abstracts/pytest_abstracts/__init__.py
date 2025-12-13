
import inspect
from functools import cached_property
from typing import Callable
from unittest.mock import MagicMock

import pytest  # type:ignore

import abstracts


class InterfaceException(Exception):
    pass


class InterfaceCheck:

    def __init__(self, iface):
        self.iface = iface

    @cached_property
    def async_methods(self):
        return tuple(
            name
            for name, fun
            in self.members.items()
            if (not name.startswith("_")
                and not isinstance(fun, property)
                and inspect.iscoroutinefunction(fun.__wrapped__)))

    @cached_property
    def async_properties(self):
        return tuple(
            name
            for name, fun
            in self.members.items()
            if (not name.startswith("_")
                and isinstance(fun, property)
                and inspect.iscoroutinefunction(fun.fget.__wrapped__)))

    @cached_property
    def dunder_methods(self):
        return tuple(
            name
            for name, fun
            in self.members.items()
            if (name.startswith("__")
                and name.endswith("__")
                and hasattr(fun, "__wrapped__")))

    @cached_property
    def properties(self):
        return tuple(
            name
            for name, fun in self.members.items()
            if isinstance(fun, property)
            and not inspect.iscoroutinefunction(fun.fget.__wrapped__))

    @cached_property
    def members(self):
        return dict(inspect.getmembers(self.iface))

    @cached_property
    def methods(self):
        return tuple(
            name
            for name, fun
            in self.members.items()
            if (not name.startswith("_")
                and not isinstance(fun, property)
                and not inspect.iscoroutinefunction(fun.__wrapped__)))

    @cached_property
    def dummy(self):
        this = self

        @abstracts.implementer(self.iface)
        class Dummy:
            for _method in this.dunder_methods:
                if _method == "__init__":
                    locals()[_method] = lambda *args, **kwargs: None
                    __super_init__ = this.iface.__init__.__wrapped__
                else:
                    locals()[_method] = getattr(
                        this.iface, _method).__wrapped__

            for _prop in this.properties:
                locals()[_prop] = property(
                    getattr(this.iface, _prop).fget.__wrapped__)

            for _async_prop in this.async_properties:
                locals()[_async_prop] = getattr(
                    this.iface, _async_prop).fget.__wrapped__

            for _method in this.methods:
                locals()[_method] = getattr(
                    this.iface, _method).__wrapped__

            for _async_method in this.async_methods:
                locals()[_async_method] = getattr(
                    this.iface, _async_method).__wrapped__

            for _local in ["_prop", "_method", "_async_method", "_async_prop"]:
                if _local in locals():
                    del locals()[_local]
            if "_local" in locals():
                del locals()["_local"]

        Dummy.__qualname__ = f"Dummy{self.iface.__name__}"
        return Dummy

    async def check(self):
        with pytest.raises(TypeError):
            self.iface()

        dummy = self.dummy()

        for name in self.dunder_methods:
            await self.check_method(dummy, name)
        for name in self.async_methods:
            await self.check_method(dummy, name)
        for name in self.async_properties:
            await self.check_method(dummy, name)
        for name in self.properties:
            self.check_property(dummy, name)

    def _call_method(self, method):
        return method(
            *([MagicMock()]
              * len(list(p
                    for name, p
                    in inspect.signature(method).parameters.items()
                    if p.kind
                    in [p.POSITIONAL_OR_KEYWORD,
                        p.POSITIONAL_ONLY,
                        p.VAR_POSITIONAL]))))

    async def check_method(self, dummy, name):
        method = getattr(dummy, name)
        if inspect.isasyncgenfunction(method):
            with pytest.raises(NotImplementedError):
                async for item in self._call_method(method):
                    pass
            return
        elif inspect.iscoroutinefunction(method):
            with pytest.raises(NotImplementedError):
                await self._call_method(method)
        elif inspect.isgeneratorfunction(method):
            with pytest.raises(NotImplementedError):
                for item in self._call_method(method):
                    pass
        elif name == "__init__":
            with pytest.raises(NotImplementedError):
                self._call_method(getattr(dummy, "__super_init__"))
        else:
            with pytest.raises(NotImplementedError):
                self._call_method(method)
        if not name.startswith("__"):
            self.has_docstring(name, method)

        if name == "__init__":
            method = getattr(dummy, "__super_init__")
        self.has_signature(name, method)

    def check_property(self, dummy, name):
        with pytest.raises(NotImplementedError):
            getattr(dummy, name)

    def has_docstring(self, name, fun):
        if not fun.__doc__:
            self._except(f"Missing docstring: {name}")

    def has_signature(self, name, fun):
        try:
            signature = inspect.signature(fun)
        except ValueError as e:
            self._except(e)
            return
        for parameter, annotations in signature.parameters.items():
            if parameter == "self":
                if not annotations.annotation == annotations.empty:
                    self._except(f"Self should not be annotated: {name}")
            elif parameter in ["args", "kwargs"]:
                # this is not the best test for *args/**kwargs
                continue
            else:
                if annotations.annotation == annotations.empty:
                    self._except(
                        f"Missing parameter hint: {name}::{parameter}")
        if signature.return_annotation == signature.empty:
            self._except(f"Missing return annotation: {name}")

    def _except(self, message):
        raise InterfaceException(message)


def _iface(type: type) -> InterfaceCheck:
    return InterfaceCheck(type)


@pytest.fixture
def iface() -> Callable:
    return _iface
