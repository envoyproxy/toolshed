
import inspect
from typing import Callable
from unittest.mock import MagicMock

import pytest  # type:ignore


class InterfaceException(Exception):
    pass


class InterfaceCheck:

    def __init__(self, iface):
        self.iface = iface

    def check(self):
        with pytest.raises(TypeError):
            self.iface()

        for name, fun in inspect.getmembers(self.iface):
            if name.startswith("__"):
                self.check_slot_method(name, fun)
            elif name.startswith("_"):
                self.check_private_method(name, fun)
            elif not hasattr(fun, "fget"):
                self.check_method(name, fun)
            else:
                self.check_property(name, fun)

    def check_method(self, name, method):
        if hasattr(method, "_fun"):
            # __wrapped__ ?
            method = method._fun
        self.has_docstring(name, method)
        self.has_signature(name, method)
        with pytest.raises(NotImplementedError):
            method(*[MagicMock()] * len(inspect.signature(method).parameters))

    def check_private_method(self, name, method):
        pass

    def check_property(self, name, prop):
        pass

        with pytest.raises(NotImplementedError):
            prop.fget()

    def check_slot_method(self, name, method):
        pass

    def has_docstring(self, name, fun):
        if not fun.__doc__:
            self._except(f"Missing docstring: {name}")
        pass

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
