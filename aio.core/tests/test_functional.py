import abc
import contextlib
import math
import types
from typing import Iterable
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
    [None, Exception, KeyError])
@pytest.mark.parametrize(
    "indexable_raises",
    [None, Exception, IndexError])
def test_collection_query_traverse(
        patches, is_mapping, mapping_raises, indexable_raises):
    query = functional.CollectionQuery("DATA")
    patched = patches(
        "isinstance",
        "CollectionQuery.traverse_mapping",
        "CollectionQuery.traverse_indexable",
        prefix="aio.core.functional.collections")
    qs = MagicMock()
    data = MagicMock()
    path = MagicMock()
    should_raise = bool(
        (is_mapping
         and mapping_raises
         and mapping_raises != Exception)
        or (not is_mapping
            and indexable_raises
            and indexable_raises != Exception))
    should_fail = bool(
        not should_raise
        and ((is_mapping and mapping_raises)
             or not is_mapping and indexable_raises))
    e = None
    mapping_error = None
    index_error = None

    with patched as (m_inst, m_mapping, m_indexable):
        m_inst.return_value = not is_mapping
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
        == [(path, int), {}])
    if is_mapping:
        assert not m_indexable.called
        assert (
            m_mapping.call_args
            == [(data, path), {}])
        if should_raise:
            assert (
                e.value.args[0]
                == (f"Unable to traverse mapping {path} "
                    f"in {qs}: {mapping_error}"))
        return
    assert not m_mapping.called
    assert (
        m_indexable.call_args
        == [(data, path), {}])
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
        "QueryDict.query_dict",
        prefix="aio.core.functional.collections")
    data = MagicMock()

    with patched as (m_query, ):
        assert query_dict(data) == m_query.return_value

    assert (
        m_query.call_args
        == [(data, ), {}])


def test_query_collection_query_dict(patches):
    query_dict = functional.QueryDict("QUERY")
    patched = patches(
        "_SearchableCollection",
        "QueryDict.query_class",
        prefix="aio.core.functional.collections")
    data = MagicMock()

    with patched as (m_searchable, m_class):
        assert (
            query_dict.query_dict(data)
            == m_class.return_value.return_value)

    assert (
        m_class.call_args
        == [(m_searchable.return_value, ), {}])
    assert (
        m_searchable.call_args
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


def test_searchable_collection_constructor():
    collection = MagicMock()
    assert (
        functional.collections._SearchableCollection(
            collection)._collection
        == collection)


def test_searchable_collection_dunder_getitem():
    collection = MagicMock()
    k = MagicMock()
    assert (
        functional.collections._SearchableCollection(
            collection).__getitem__(k)
        == collection.__getitem__.return_value)
    assert (
        collection.__getitem__.call_args
        == [(k, ), {}])


def test_searchable_collection_dunder_iter():
    collection = MagicMock()
    coll = functional.collections._SearchableCollection(collection)
    items = [f"C{i}" for i in range(0, 5)]
    collection.__iter__.return_value = items
    assert list(coll.__iter__()) == items
    assert (
        collection.__iter__.call_args
        == [(), {}])


def test_searchable_collection_dunder_len():
    collection = MagicMock()
    assert (
        functional.collections._SearchableCollection(
            collection).__len__()
        == collection.__len__.return_value)
    assert (
        collection.__len__.call_args
        == [(), {}])


@pytest.mark.parametrize("item_count", range(0, 20))
@pytest.mark.parametrize("batch_size", range(0, 7))
def test_batches(item_count, batch_size):
    items = [MagicMock() for m in range(0, item_count)]
    actual_batch_size = batch_size or 1
    batch_iter = functional.batches(items, batch_size)
    assert isinstance(batch_iter, types.GeneratorType)
    batches = list(batch_iter)
    assert all(len(b) <= actual_batch_size for b in batches)
    assert sum(len(b) for b in batches) == item_count
    assert (
        len(batches)
        == (0
            if not item_count
            else (
                math.floor(item_count / actual_batch_size)
                + (1
                   if item_count % actual_batch_size
                   else 0))))
    results = []
    for b in batches:
        for result in b:
            results.append(result)
    assert results == items


@pytest.mark.parametrize("is_str_or_bytes", [True, False])
@pytest.mark.parametrize("is_iterable", [True, False])
@pytest.mark.parametrize("max_batch_size", [None, 0, 23])
@pytest.mark.parametrize("min_batch_size", [None, 0, 23])
def test_batch_jobs(
        patches, is_str_or_bytes, is_iterable, max_batch_size, min_batch_size):
    patched = patches(
        "len",
        "isinstance",
        "max",
        "min",
        "os",
        "round",
        "type",
        "batches",
        "typed",
        prefix="aio.core.functional.utils")
    jobs = MagicMock()
    kwargs = {}
    if max_batch_size is not None:
        kwargs["max_batch_size"] = max_batch_size
    if min_batch_size is not None:
        kwargs["min_batch_size"] = min_batch_size

    def isinst(item, _type):
        if _type == Iterable:
            return is_iterable
        return is_str_or_bytes

    with patched as patchy:
        (m_len, m_isinst, m_max, m_min, m_os, m_round, m_type,
         m_batches, m_typed) = patchy
        m_isinst.side_effect = isinst
        if not is_iterable or is_str_or_bytes:
            with pytest.raises(functional.exceptions.BatchedJobsError) as e:
                functional.batch_jobs(jobs, **kwargs)
        else:
            assert (
                functional.batch_jobs(jobs, **kwargs)
                == m_batches.return_value)

    assert (
        m_isinst.call_args_list[0]
        == [(jobs, Iterable), {}])
    if not is_iterable or is_str_or_bytes:
        assert not m_os.proc_count.called
        assert not m_round.called
        assert not m_len.called
        assert not m_min.called
        assert not m_max.called
        assert not m_batches.called
        assert not m_typed.called
        assert (
            e.value.args[0]
            == f"Wrong type for `batch_jobs` ({m_type.return_value}: {jobs}")
        assert (
            m_type.call_args
            == [(jobs, ), {}])
    if not is_iterable:
        assert len(m_isinst.call_args_list) == 1
        return
    assert (
        m_isinst.call_args_list[1]
        == [(jobs, (str, bytes)), {}])
    if is_str_or_bytes:
        return
    assert not m_type.called
    assert (
        m_os.cpu_count.call_args
        == [(), {}])
    assert (
        m_len.call_args
        == [(jobs, ), {}])
    assert (
        m_round.call_args
        == [(m_len.return_value.__truediv__.return_value, ),
            {}])
    assert (
        m_len.return_value.__truediv__.call_args
        == [(m_os.cpu_count.return_value, ), {}])
    batch_count = m_round.return_value
    if max_batch_size:
        assert (
            m_min.call_args
            == [(batch_count, max_batch_size), {}])
        batch_count = m_min.return_value
    else:
        assert not m_min.called
    if min_batch_size:
        assert (
            m_max.call_args
            == [(batch_count, min_batch_size), {}])
        batch_count = m_max.return_value
    else:
        assert not m_max.called
    assert (
        m_typed.call_args
        == [(Iterable, jobs), {}])
    assert (
        m_batches.call_args
        == [(m_typed.return_value, ),
            dict(batch_size=batch_count)])
