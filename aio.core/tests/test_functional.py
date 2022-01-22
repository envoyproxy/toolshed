import abc
import types
from unittest.mock import AsyncMock

import pytest

import abstracts

from aio.core import functional


# TODO: add a test to make sure that async loading multiple
#   instances of the same class dont write to each others caches


@pytest.mark.parametrize("cache", [None, True, False])
@pytest.mark.parametrize("raises", [True, False])
@pytest.mark.parametrize("result", [None, False, "X", 23])
async def test_functional_async_property(cache, raises, result):
    m_async = AsyncMock(return_value=result)

    class SomeError(Exception):
        pass

    if cache is None:
        decorator = functional.async_property
        iter_decorator = functional.async_property
    else:
        decorator = functional.async_property(cache=cache)
        iter_decorator = functional.async_property(cache=cache)

    items = [f"ITEM{i}" for i in range(0, 5)]

    class Klass:

        @decorator
        async def prop(self):
            """This prop deserves some docs."""
            if raises:
                await m_async()
                raise SomeError("AN ERROR OCCURRED")
            else:
                return await m_async()

        @iter_decorator
        async def iter_prop(self):
            """This prop also deserves some docs."""
            if raises:
                await m_async()
                raise SomeError("AN ITERATING ERROR OCCURRED")
            result = await m_async()
            for item in items:
                yield item, result

    klass = Klass()

    # The class.prop should be an instance of async_prop
    # and should have the name and docs of the wrapped method.
    assert isinstance(
        type(klass).prop,
        functional.async_property)
    assert (
        type(klass).prop.__doc__
        == "This prop deserves some docs.")
    assert (
        type(klass).prop.name
        == "prop")

    if raises:
        with pytest.raises(SomeError) as e:
            await klass.prop

        with pytest.raises(SomeError) as e2:
            async for result in klass.iter_prop:
                pass

        assert (
            e.value.args[0]
            == 'AN ERROR OCCURRED')
        assert (
            e2.value.args[0]
            == 'AN ITERATING ERROR OCCURRED')
        assert (
            m_async.call_args_list
            == [[(), {}]] * 2)
        return

    # results can be repeatedly awaited
    assert await klass.prop == result
    assert await klass.prop == result

    # results can also be repeatedly iterated
    results1 = []
    async for returned_result in klass.iter_prop:
        results1.append(returned_result)
    assert results1 == [(item, result) for item in items]

    results2 = []
    async for returned_result in klass.iter_prop:
        results2.append(returned_result)

    if not cache:
        assert results2 == results1
        assert (
            m_async.call_args_list
            == [[(), {}]] * 4)
        assert not hasattr(klass, functional.async_property.cache_name)
        return

    # with cache we can keep awaiting the result but the fun
    # is still only called once
    assert await klass.prop == result
    assert await klass.prop == result
    assert (
        m_async.call_args_list
        == [[(), {}]] * 2)

    iter_prop = getattr(
        klass, functional.async_property.cache_name)["iter_prop"]
    assert isinstance(iter_prop, types.AsyncGeneratorType)
    assert (
        getattr(klass, functional.async_property.cache_name)
        == dict(prop=m_async.return_value, iter_prop=iter_prop))

    # cached iterators dont give any more results once they are done
    assert results2 == []


@pytest.mark.parametrize("cache", [True, False])
async def test_functional_async_property_abstract(cache):
    if cache:
        decorator = functional.async_property
    else:
        decorator = functional.async_property(cache=cache)

    class Klass:

        @decorator
        @abc.abstractmethod
        async def prop(self):
            pass

        @decorator
        @abstracts.interfacemethod
        async def iface_prop(self):
            pass

    assert Klass.prop.__isabstractmethod__ is True
    assert Klass.iface_prop.__isabstractmethod__ is True


def test_functional_async_property_is_cached(cache):
    is_cached = functional.async_property.is_cached
    cache_name = functional.async_property.cache_name

    class Klass:
        pass

    obj = Klass()
    assert not is_cached(obj, "FOO")
    setattr(obj, cache_name, {})
    assert not is_cached(obj, "FOO")
    getattr(obj, cache_name)["BAR"] = 7
    assert not is_cached(obj, "FOO")
    getattr(obj, cache_name)["FOO"] = 23
    assert is_cached(obj, "FOO")
    getattr(obj, cache_name)["FOO"] = None
    assert is_cached(obj, "FOO")
    del getattr(obj, cache_name)["FOO"]
    assert not is_cached(obj, "FOO")
    delattr(obj, cache_name)
    assert not is_cached(obj, "FOO")
