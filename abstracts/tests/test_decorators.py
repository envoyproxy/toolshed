from abc import abstractmethod
from unittest.mock import MagicMock

import pytest

import abstracts


class AFoo(metaclass=abstracts.Abstraction):

    @classmethod
    @abstractmethod
    def do_something_classy(cls):
        pass

    @abstractmethod
    def do_something(self):
        """Do something"""
        raise NotImplementedError


class ABar(metaclass=abstracts.Abstraction):

    @abstractmethod
    def do_something_else(self):
        """Do something else"""
        raise NotImplementedError


class Baz:

    def do_nothing(self):
        pass


@pytest.mark.parametrize(
    "implements",
    [(), AFoo, (AFoo, ), (AFoo, ABar), (AFoo, ABar, Baz), Baz])
def test_decorators_implementer(patches, implements):
    iterable_implements = (
        implements
        if isinstance(implements, tuple)
        else (implements, ))
    should_fail = any(
        not isinstance(impl, abstracts.Abstraction)
        for impl
        in iterable_implements)

    if should_fail:
        with pytest.raises(TypeError):
            _implementer(implements)
        return

    implementer = _implementer(implements)
    for impl in iterable_implements:
        assert issubclass(implementer, impl)
    assert (
        implementer.__name__
        == implementer.__qualname__
        == "ImplementationOfAnImplementer")
    assert (
        implementer.__doc__
        == 'A test implementation of an implementer')


def _implementer(implements):

    @abstracts.implementer(implements)
    class ImplementationOfAnImplementer:
        """A test implementation of an implementer"""

        @classmethod
        def do_something_classy(cls):
            pass

        def do_something(self):
            pass

        def do_something_else(self):
            pass

        def do_nothing(self):
            pass

    return ImplementationOfAnImplementer


def test_decorators_interfacemethod():
    iface_mock = MagicMock()
    method_mock = MagicMock()

    class Interfacey:

        @abstracts.interfacemethod
        def iface_method(self):
            method_mock()

        @property
        @abstracts.interfacemethod
        def iface_property(self):
            iface_mock()

    iface = Interfacey()

    with pytest.raises(NotImplementedError):
        iface.iface_method()

    with pytest.raises(NotImplementedError):
        iface.iface_property

    assert iface.iface_method.__isabstractmethod__
    assert iface.iface_method.__isinterfacemethod__
    Interfacey.iface_property.fget.__isabstractmethod__
    Interfacey.iface_property.fget.__isinterfacemethod__

    assert not iface_mock.called
    assert not method_mock.called

    with pytest.raises(NotImplementedError):
        Interfacey.iface_method(iface)

    with pytest.raises(NotImplementedError):
        Interfacey.iface_property.__get__(iface)

    assert not iface_mock.called
    assert not method_mock.called

    # hit the method lines to add coverage
    Interfacey.iface_property.fget.__wrapped__(iface)
    Interfacey.iface_method.__wrapped__(iface)
