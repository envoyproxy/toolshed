
import abc
import contextlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.core import functional, output


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
    with pytest.raises(output.exceptions.BufferUtilError):
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


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_buffering(patches, args, kwargs):

    patched = patches(
        "buffered",
        prefix="aio.core.functional.output")

    marker = MagicMock()
    fun = MagicMock()

    def run_fun(*args, **kwargs):
        return marker.in_context

    fun.side_effect = run_fun

    @contextlib.contextmanager
    def mock_buffered(stdout, stderr):
        marker.in_context = "IN CONTEXT"
        yield
        marker.in_context = "NOT IN CONTEXT"

    with patched as (m_buffered, ):
        m_buffered.side_effect = mock_buffered
        assert (
            functional.buffering(fun, "STDOUT", "STDERR", *args, **kwargs)
            == "IN CONTEXT")

    assert (
        m_buffered.call_args
        == [("STDOUT", "STDERR"), {}])
    assert (
        fun.call_args
        == [tuple(args), kwargs])


@pytest.mark.parametrize("stdout", [None, False, "", "STDOUT"])
@pytest.mark.parametrize("stderr", [None, False, "", "STDERR"])
@pytest.mark.parametrize("both", [None, False, "", "BOTH"])
async def test_capturing(patches, stdout, stderr, both):
    patched = patches(
        "output.BufferedOutputs",
        prefix="aio.core.functional.output")
    kwargs = {}
    if stdout is not None:
        kwargs["stdout"] = stdout
    if stderr is not None:
        kwargs["stderr"] = stderr
    if both is not None:
        kwargs["both"] = both
    should_fail = (
        not any([stdout, stderr, both])
        or (both
            and (stdout or stderr)))
    outputs = {}
    stdout = (both if both else stdout)
    if stdout:
        outputs["stdout"] = stdout
    stderr = (both if both else stderr)
    if stderr:
        outputs["stderr"] = stderr

    with patched as (m_output, ):
        if should_fail:
            with pytest.raises(output.exceptions.CapturingException) as e:
                async with functional.capturing(**kwargs):
                    pass
            if not both:
                assert (
                    e.value.args[0]
                    == ("You must supply either `both`, "
                        "or one of `stdout` and `stderr`"))
            else:
                assert (
                    e.value.args[0]
                    == ("If you supply `both`, `stdout` "
                        "and `stderr` should not be set"))

        else:
            async with functional.capturing(**kwargs) as buffer:
                assert buffer == m_output.return_value.__aenter__.return_value

    if should_fail:
        assert not m_output.called
        return

    assert (
        m_output.call_args
        == [(outputs, ), {}])


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize("stdout", [None, False, "", "STDOUT"])
@pytest.mark.parametrize("stderr", [None, False, "", "STDERR"])
@pytest.mark.parametrize("both", [None, False, "", "BOTH"])
@pytest.mark.parametrize("pool", [None, False, "", "POOL"])
@pytest.mark.parametrize("any_set", [True, False])
async def test_threaded(patches, args, stdout, stderr, both, pool, any_set):
    patched = patches(
        "any",
        "asyncio",
        "dict",
        "functional",
        prefix="aio.core.functional.process")
    fun = MagicMock()
    kwargs = {}
    if stdout is not None:
        kwargs["stdout"] = stdout
    if stderr is not None:
        kwargs["stderr"] = stderr
    if both is not None:
        kwargs["both"] = both
    if pool is not None:
        kwargs["pool"] = pool

    with patched as (m_any, m_aio, m_dict, m_func):
        m_any.return_value = any_set
        executor = AsyncMock()
        m_aio.get_running_loop.return_value.run_in_executor = executor
        get = MagicMock()
        m_func.capturing.return_value.__aenter__.return_value.get = get
        assert (
            await functional.threaded(fun, *args, **kwargs)
            == (m_aio.get_running_loop.return_value
                     .run_in_executor.return_value))

    assert (
        m_aio.get_running_loop.call_args
        == [(), {}])
    assert (
        m_any.call_args
        == [([stdout, stderr, both], ), {}])
    if not any_set:
        assert not m_dict.called
        assert not m_func.capturing.called
        assert (
            executor.call_args
            == [(pool, fun, *args), {}])
        return
    assert (
        m_dict.call_args
        == [(), dict(stdout=stdout, stderr=stderr, both=both)])
    assert (
        m_func.capturing.call_args
        == [(m_dict.return_value, ), {}])
    assert (
        executor.call_args
        == [(pool, m_func.buffering, fun,
             get.return_value,
             get.return_value,
             *args), {}])
    assert (
        get.call_args_list
        == [[(out, ), {}] for out in ["stdout", "stderr"]])


def test_utils_junzip(patches):
    data = MagicMock()
    patched = patches(
        "gzip",
        "json",
        prefix="aio.core.functional.utils")

    with patched as (m_gzip, m_json):
        assert (
           functional.utils.junzip(data)
           == m_json.loads.return_value)

    assert (
        m_json.loads.call_args
        == [(m_gzip.decompress.return_value, ), {}])
    assert (
        m_gzip.decompress.call_args
        == [(data, ), {}])


@pytest.mark.parametrize(
    "casted",
    [(), [], False, None, "", "X", ["Y"]])
def test_typed(patches, casted):
    patched = patches(
        "trycast",
        "textwrap",
        "str",
        prefix="aio.core.functional.utils")

    value = MagicMock()

    with patched as (m_try, m_wrap, m_str):
        m_try.return_value = casted

        if casted is None:
            with pytest.raises(functional.exceptions.TypeCastingError) as e:
                functional.utils.typed("TYPE", value)

            assert (
                e.value.args[0]
                == ("Value has wrong type or shape for Type "
                    f"TYPE: {m_wrap.shorten.return_value}"))
            assert (
                m_wrap.shorten.call_args
                == [(m_str.return_value, ),
                    dict(width=10, placeholder="...")])
            assert (
                m_str.call_args
                == [(value, ), {}])
        else:
            assert functional.utils.typed("TYPE", value) == value
            assert not m_wrap.shorten.called
            assert not m_str.called

    assert (
        m_try.call_args
        == [("TYPE", value), {}])


def test_collection_query_constructor():
    data = MagicMock()
    query = functional.CollectionQuery(data)
    assert query.data == data


def test_collection_query_dunder_call(patches):
    query = functional.CollectionQuery("DATA")
    patched = patches(
        "dict",
        "CollectionQuery.iter_queries",
        prefix="aio.core.functional.collections")
    qs = MagicMock()

    with patched as (m_dict, m_queries):
        assert query(qs) == m_dict.return_value

    assert (
        m_dict.call_args
        == [(m_queries.return_value, ), {}])
    assert (
        m_queries.call_args
        == [(qs, ), {}])


def test_collection_query_dunder_getitem(patches):
    query = functional.CollectionQuery("DATA")
    patched = patches(
        "CollectionQuery.query",
        prefix="aio.core.functional.collections")
    qs = MagicMock()

    with patched as (m_query, ):
        assert query[qs] == m_query.return_value

    assert (
        m_query.call_args
        == [(qs, ), {}])


def test_collection_query_iter_queries(patches):
    query = functional.CollectionQuery("DATA")
    patched = patches(
        "str",
        "CollectionQuery.query",
        prefix="aio.core.functional.collections")
    qs = MagicMock()
    items = [(i, f"I{i}") for i in range(0, 5)]
    qs.items.return_value = items

    with patched as (m_str, m_query):
        result = query.iter_queries(qs)
        assert isinstance(result, types.GeneratorType)
        assert (
            list(result)
            == [(m_str.return_value, m_query.return_value)
                for i in items])

    assert (
        m_str.call_args_list
        == [[(item[0], ), {}] for item in items])
    assert (
        m_query.call_args_list
        == [[(item[1], ), {}] for item in items])


@pytest.mark.parametrize(
    "parts", [[], [f"PART{i}" for i in range(0, 5)]])
def test_collection_query_query(patches, parts):
    data = MagicMock()
    query = functional.CollectionQuery(data)
    patched = patches(
        "CollectionQuery.spliterator",
        "CollectionQuery.traverse",
        prefix="aio.core.functional.collections")
    qs = MagicMock()

    with patched as (m_split, m_traverse):
        m_split.return_value = parts
        assert (
            query.query(qs)
            == (m_traverse.return_value
                if parts
                else data))

    calls = []
    for i, part in enumerate(parts):
        calls.append(
            (qs, data, part)
            if i == 0
            else (qs, m_traverse.return_value, part))
    assert (
        m_traverse.call_args_list
        == [[call, {}] for call in calls])
    assert (
        m_split.call_args
        == [(qs, ), {}])


@pytest.mark.parametrize("is_int", [True, False])
def test_collection_query_spliterator(patches, is_int):
    query = functional.CollectionQuery("DATA")
    patched = patches(
        "isinstance",
        prefix="aio.core.functional.collections")
    qs = MagicMock()
    int_items = [i for i in range(0, 5)]
    intable_items = [str(i) for i in range(5, 10)]
    str_items = [str(f"I{i}") for i in range(5, 10)]
    items = (
        int_items
        + intable_items
        + str_items)
    qs.split.return_value = items

    with patched as (m_inst, ):
        m_inst.return_value = is_int
        result = query.spliterator(qs)
        assert isinstance(result, types.GeneratorType)
        result = list(result)

    if is_int:
        assert not qs.split.called
        assert result == [qs]
        return
    assert (
        result
        == (int_items
            + [int(i) for i in intable_items]
            + str_items))
    assert (
        qs.split.call_args
        == [("/", ), {}])


@pytest.mark.parametrize("is_mapping", [True, False])
@pytest.mark.parametrize(
    "mapping_raises",
    [None, Exception, KeyError, functional.exceptions.TypeCastingError])
@pytest.mark.parametrize(
    "indexable_raises",
    [None, Exception, IndexError, functional.exceptions.TypeCastingError])
def test_collection_query_traverse(
        patches, is_mapping, mapping_raises, indexable_raises):
    query = functional.CollectionQuery("DATA")
    patched = patches(
        "isinstance",
        "typed",
        "Any",
        "Dict",
        "Indexable",
        "SearchKey",
        "CollectionQuery.traverse_mapping",
        "CollectionQuery.traverse_indexable",
        prefix="aio.core.functional.collections")
    qs = MagicMock()
    data = MagicMock()
    path = MagicMock()
    should_raise = (
        (is_mapping
         and mapping_raises
         and mapping_raises != Exception)
        or (not is_mapping
            and indexable_raises
            and indexable_raises != Exception))
    should_fail = (
        not should_raise
        and ((is_mapping and mapping_raises)
             or not is_mapping and indexable_raises))
    e = None
    mapping_error = None
    index_error = None

    with patched as patchy:
        (m_inst, m_typed, m_tany, m_tdict, m_tindex, m_tkey,
         m_mapping, m_indexable) = patchy
        m_inst.return_value = is_mapping
        if mapping_raises:
            mapping_error = mapping_raises("A MAPPING ERROR OCCURRED")
            m_mapping.side_effect = mapping_error
        if indexable_raises:
            index_error = indexable_raises("AN INDEXABLE ERROR OCCURRED")
            m_indexable.side_effect = index_error
        if should_raise:
            raises = functional.exceptions.CollectionQueryError
            with pytest.raises(raises) as e:
                query.traverse(qs, data, path)
        elif should_fail:
            with pytest.raises(Exception) as e:
                query.traverse(qs, data, path)
        else:
            assert(
                query.traverse(qs, data, path)
                == (m_mapping.return_value
                    if is_mapping
                    else m_indexable.return_value))

    assert (
        m_inst.call_args
        == [(data, dict), {}])
    if is_mapping:
        assert not m_indexable.called
        assert (
            m_mapping.call_args
            == [(m_typed.return_value, path), {}])
        assert (
            m_typed.call_args_list
            == [[(m_tdict.__getitem__.return_value, data),
                 {}]])
        assert (
            m_tdict.__getitem__.call_args
            == [((m_tkey, m_tany), ), {}])
        if should_raise:
            assert (
                e.value.args[0]
                == (f"Unable to traverse mapping {path} "
                    f"in {qs}: {mapping_error}"))
        return
    assert not m_mapping.called
    assert (
        m_indexable.call_args
        == [(m_typed.return_value,
             m_typed.return_value), {}])
    assert (
        m_typed.call_args_list
        == [[(m_tindex, data), {}],
            [(int, path), {}]])
    if should_raise:
        assert (
            e.value.args[0]
            == f"Unable to traverse index {path} in {qs}: {index_error}")


def test_collection_query_traverse_mapping():
    query = functional.CollectionQuery("DATA")
    data = MagicMock()
    key = MagicMock()
    assert (
        query.traverse_mapping(data, key)
        == data.__getitem__.return_value)
    assert (
        data.__getitem__.call_args
        == [(key, ), {}])


def test_collection_query_traverse_indexable():
    query = functional.CollectionQuery("DATA")
    data = MagicMock()
    key = MagicMock()
    assert (
        query.traverse_indexable(data, key)
        == data.__getitem__.return_value)
    assert (
        data.__getitem__.call_args
        == [(key, ), {}])


def test_query_dict_constructor():
    query = MagicMock()
    qdict = functional.QueryDict(query)
    assert qdict.query == query
    assert qdict.query_class == functional.CollectionQuery


def test_query_dict_dunder_call(patches):
    query_dict = functional.QueryDict("QUERY")
    patched = patches(
        "typed",
        "SearchableCollection",
        "QueryDict.query_dict",
        prefix="aio.core.functional.collections")
    data = MagicMock()

    with patched as (m_typed, m_searchable, m_query):
        assert query_dict(data) == m_query.return_value

    assert (
        m_typed.call_args
        == [(m_searchable, data), {}])
    assert (
        m_query.call_args
        == [(m_typed.return_value, ), {}])


def test_query_collection_query_dict(patches):
    query_dict = functional.QueryDict("QUERY")
    patched = patches(
        "QueryDict.query_class",
        prefix="aio.core.functional.collections")
    data = MagicMock()

    with patched as (m_class, ):
        assert (
            query_dict.query_dict(data)
            == m_class.return_value.return_value)

    assert (
        m_class.call_args
        == [(data, ), {}])
    assert (
        m_class.return_value.call_args
        == [("QUERY", ), {}])


@pytest.mark.parametrize(
    "queries",
    [{},
     {f"QK{i}": f"QV{i}" for i in range(0, 5)}])
def test_qdict(patches, queries):
    patched = patches(
        "QueryDict",
        prefix="aio.core.functional.collections")

    with patched as (m_qdict, ):
        assert functional.qdict(**queries) == m_qdict.return_value
