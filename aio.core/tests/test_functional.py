
import abc
import contextlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

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


@pytest.mark.parametrize("predicate", [True, False])
@pytest.mark.parametrize("result", [True, False])
async def test_collections_async_iterator(patches, predicate, result):
    patched = patches(
        "maybe_coro",
        prefix="aio.core.functional.collections")
    results = []
    kwargs = {}
    n = 1
    if predicate:
        kwargs["predicate"] = MagicMock()
    if result:
        n = 2
        kwargs["result"] = MagicMock()

    async def iterator():
        for x in range(0, 10):
            yield x

    predicate_mock = AsyncMock(side_effect=lambda x: x % 2)
    result_mock = AsyncMock(side_effect=lambda x: x * 2)
    coro_mock = AsyncMock(side_effect=lambda x: x)

    def maybe(arg):
        if arg == kwargs.get("predicate"):
            return predicate_mock
        elif arg == kwargs.get("result"):
            return result_mock
        return coro_mock

    with patched as (m_maybe, ):
        m_maybe.side_effect = maybe
        async for item in functional.async_iterator(iterator(), **kwargs):
            results.append(item)

    if result:
        assert not coro_mock.called
    else:
        assert not result_mock.called
    if predicate:
        assert (
            results
            == [x * n for x in range(0, 10) if x % 2])
        assert (
            predicate_mock.call_args_list
            == [[(x, ), {}]
                for x
                in range(0, 10)])
        if result:
            assert (
                result_mock.call_args_list
                == [[(x, ), {}]
                    for x
                    in range(0, 10)
                    if x % 2])
        else:
            assert (
                coro_mock.call_args_list
                == [[(x, ), {}]
                    for x
                    in range(0, 10)
                    if x % 2])
    else:
        assert not predicate_mock.called
        assert (
            results
            == [x * n for x in range(0, 10)])
        if result:
            assert (
                result_mock.call_args_list
                == [[(x, ), {}]
                    for x
                    in range(0, 10)])
        else:
            assert (
                coro_mock.call_args_list
                == [[(x, ), {}]
                    for x
                    in range(0, 10)])


@pytest.mark.parametrize("predicate", [None, False, "PREDICATE"])
@pytest.mark.parametrize("result", [None, False, "RESULT"])
async def test_collections_async_list(patches, predicate, result):
    patched = patches(
        "list",
        "async_iterator",
        prefix="aio.core.functional.collections")

    iterator_instance = MagicMock()
    kwargs = {}
    if predicate is not None:
        kwargs["predicate"] = predicate
    if result is not None:
        kwargs["result"] = result

    async def iterator(it, **kwargs):
        for x in range(0, 10):
            yield x

    with patched as (m_list, m_iter):
        m_iter.side_effect = iterator
        assert (
            await functional.async_list(
                iterator_instance, **kwargs)
            == m_list.return_value)

    kwargs["predicate"] = predicate
    kwargs["result"] = result
    assert (
        m_iter.call_args
        == [(iterator_instance, ), kwargs])
    assert (
        m_list.return_value.append.call_args_list
        == [[(x, ), {}]
            for x in range(0, 10)])


@pytest.mark.parametrize("predicate", [None, False, "PREDICATE"])
@pytest.mark.parametrize("result", [None, False, "RESULT"])
async def test_collections_async_set(patches, predicate, result):
    patched = patches(
        "set",
        "async_iterator",
        prefix="aio.core.functional.collections")

    iterator_instance = MagicMock()
    kwargs = {}
    if predicate is not None:
        kwargs["predicate"] = predicate
    if result is not None:
        kwargs["result"] = result

    async def iterator(it, **kwargs):
        for x in range(0, 10):
            yield x

    with patched as (m_set, m_iter):
        m_iter.side_effect = iterator
        assert (
            await functional.async_set(
                iterator_instance, **kwargs)
            == m_set.return_value)

    kwargs["predicate"] = predicate
    kwargs["result"] = result
    assert (
        m_iter.call_args
        == [(iterator_instance, ), kwargs])
    assert (
        m_set.return_value.add.call_args_list
        == [[(x, ), {}]
            for x in range(0, 10)])


@pytest.mark.parametrize("fork", [None, True, False])
async def test_collections_async_map(patches, fork):
    patched = patches(
        "futures",
        "list",
        "map",
        prefix="aio.core.functional.process")
    kwargs = {}
    if fork is not None:
        kwargs["fork"] = fork
    future_results = [MagicMock() for x in range(0, 10)]
    results = []
    iterable = list(range(0, 7))
    fun = MagicMock()

    def iterator(result_futures):
        for x in future_results:
            yield x

    with patched as (m_futures, m_list, m_map):
        m_futures.as_completed.side_effect = iterator

        async for result in functional.async_map(fun, iterable, **kwargs):
            results.append(result)

        anon_fun = m_map.call_args[0][0]
        anon_fun("X")

    assert (
        results
        == [x.result.return_value
            for x
            in future_results])
    if fork:
        assert not m_futures.ThreadPoolExecutor.called
        assert (
            m_futures.ProcessPoolExecutor.call_args
            == [(), {}])
        assert (
            (m_futures.ProcessPoolExecutor.return_value
                      .__enter__.return_value.submit.call_args)
            == [(fun, "X"), {}])
    else:
        assert not m_futures.ProcessPoolExecutor.called
        assert (
            m_futures.ThreadPoolExecutor.call_args
            == [(), {}])
        assert (
            (m_futures.ThreadPoolExecutor.return_value
                      .__enter__.return_value.submit.call_args)
            == [(fun, "X"), {}])
    assert (
        m_list.call_args
        == [(m_map.return_value, ), {}])
    assert (
        m_map.call_args
        == [(anon_fun, iterable), {}])


@pytest.mark.parametrize("awaitable", [True, False])
async def test_collections_maybe_awaitable(patches, awaitable):
    patched = patches(
        "asyncio",
        "inspect",
        prefix="aio.core.functional.utils")
    result = MagicMock()

    with patched as (m_aio, m_inspect):
        m_inspect.iscoroutine.return_value = awaitable
        assert (
            functional.maybe_awaitable(result)
            == (result
                if awaitable
                else m_aio.sleep.return_value))

    if awaitable:
        assert not m_aio.sleep.called
    else:
        assert (
            m_aio.sleep.call_args
            == [(0, ), dict(result=result)])


@pytest.mark.parametrize("iscoro", [True, False])
async def test_collections_maybe_coro(patches, iscoro):
    patched = patches(
        "inspect",
        prefix="aio.core.functional.utils")
    fun = (
        AsyncMock()
        if iscoro
        else MagicMock())

    with patched as (m_inspect, ):
        m_inspect.iscoroutinefunction.return_value = iscoro
        result = functional.maybe_coro(fun)
        assert (
            await result("ARG1", "ARG2", foo="BAR")
            == fun.return_value)

    assert (
        fun.call_args
        == [("ARG1", "ARG2"), dict(foo="BAR")])


@pytest.mark.parametrize("collector", [None, False, "COLLECTOR"])
@pytest.mark.parametrize("iterator", [None, False, "ITERATOR"])
@pytest.mark.parametrize("predicate", [None, False, "PREDICATE"])
@pytest.mark.parametrize("result", [None, False, "RESULT"])
def test_generator_awaitablegenerator_constructor(
        collector, iterator, predicate, result):
    kwargs = {}
    if collector is not None:
        kwargs["collector"] = collector
    if iterator is not None:
        kwargs["iterator"] = iterator
    if predicate is not None:
        kwargs["predicate"] = predicate
    if result is not None:
        kwargs["result"] = result
    generator = functional.AwaitableGenerator("GENERATOR", **kwargs)
    kwargs.pop("collector", None)
    assert generator.generator == "GENERATOR"
    assert generator.collector == collector or functional.async_list
    assert generator.iterator == iterator or functional.async_list
    assert generator.predicate == predicate
    assert generator.result == result
    assert (
        generator.iter_kwargs
        == dict(predicate=generator.predicate,
                result=generator.result))
    assert "iter_kwargs" not in generator.__dict__


async def test_generator_awaitable_generator_dunder_aiter(patches):
    generator = functional.AwaitableGenerator("GENERATOR")
    patched = patches(
        ("AwaitableGenerator.iterable",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.functional.generator")
    results = []

    async def someiterfun():
        for x in range(0, 5):
            yield x

    with patched as (m_iterable, ):
        m_iterable.side_effect = someiterfun
        async for result in generator:
            results.append(result)

    assert results == list(range(0, 5))


async def test_generator_awaitable_generator_dunder_await(patches):
    generator = functional.AwaitableGenerator("GENERATOR")
    patched = patches(
        ("AwaitableGenerator.awaitable",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.functional.generator")

    async def somefun():
        return "FUN"

    with patched as (m_awaitable, ):
        m_awaitable.side_effect = somefun
        assert await generator == "FUN"


async def test_generator_awaitable_generator_awaitable(patches):
    collector = MagicMock()
    generator = functional.AwaitableGenerator("GENERATOR", collector=collector)
    patched = patches(
        ("AwaitableGenerator.iter_kwargs",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.functional.generator")
    kwargs = dict(foo="BAR")

    with patched as (m_kwargs, ):
        m_kwargs.return_value = kwargs
        assert (
            generator.awaitable
            == collector.return_value)

    assert (
        collector.call_args
        == [("GENERATOR", ), kwargs])
    assert "awaitable" not in generator.__dict__


async def test_generator_awaitable_generator_iterable(patches):
    iterator = MagicMock()
    generator = functional.AwaitableGenerator("GENERATOR", iterator=iterator)
    patched = patches(
        ("AwaitableGenerator.iter_kwargs",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.functional.generator")
    kwargs = dict(foo="BAR")

    with patched as (m_kwargs, ):
        m_kwargs.return_value = kwargs
        assert (
            generator.iterable
            == iterator.return_value)

    assert (
        iterator.call_args
        == [("GENERATOR", ), kwargs])
    assert "awaitable" not in generator.__dict__


def test_util_buffered_stdout():
    stdout = []

    with functional.buffered(stdout=stdout):
        print("test1")
        print("test2")
        sys.stdout.write("test3\n")
        sys.stderr.write("error0\n")

    assert stdout == ["test1", "test2", "test3"]


def test_util_buffered_stderr():
    stderr = []

    with functional.buffered(stderr=stderr):
        print("test1")
        print("test2")
        sys.stdout.write("test3\n")
        sys.stderr.write("error0\n")
        sys.stderr.write("error1\n")

    assert stderr == ["error0", "error1"]


def test_util_buffered_stdout_stderr():
    stdout = []
    stderr = []

    with functional.buffered(stdout=stdout, stderr=stderr):
        print("test1")
        print("test2")
        sys.stdout.write("test3\n")
        sys.stderr.write("error0\n")
        sys.stderr.write("error1\n")

    assert stdout == ["test1", "test2", "test3"]
    assert stderr == ["error0", "error1"]


def test_util_buffered_no_stdout_stderr():
    with pytest.raises(functional.exceptions.BufferUtilError):
        with functional.buffered():
            pass


def test_util_nested():

    fun1_args = []
    fun2_args = []

    @contextlib.contextmanager
    def fun1(arg):
        fun1_args.append(arg)
        yield "FUN1"

    @contextlib.contextmanager
    def fun2(arg):
        fun2_args.append(arg)
        yield "FUN2"

    with functional.nested(fun1("A"), fun2("B")) as (fun1_yield, fun2_yield):
        assert fun1_yield == "FUN1"
        assert fun2_yield == "FUN2"

    assert fun1_args == ["A"]
    assert fun2_args == ["B"]
