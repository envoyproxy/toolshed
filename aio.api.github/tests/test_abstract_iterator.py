
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import gidgethub

import abstracts

from aio.api import github


@abstracts.implementer(github.AGithubIterator)
class DummyGithubIterator:
    pass


@pytest.mark.parametrize(
    "args", [(), tuple(f"ARG{i}" for i in range(0, 3))])
@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 3)}])
def test_abstract_iterator_constructor(args, kwargs):
    iterator = DummyGithubIterator("API", "QUERY", *args, **kwargs)
    assert iterator.api == "API"
    assert iterator.query == "QUERY"
    assert iterator.args == args
    assert iterator.kwargs == kwargs


async def test_abstract_iterator_dunder_aiter(iters, patches):
    iterator = DummyGithubIterator("API", "QUERY")
    iterator.args = iters(tuple, count=3)
    iterator.kwargs = iters(dict, count=3)
    patched = patches(
        "AGithubIterator.inflate",
        prefix="aio.api.github.abstract.iterator")
    iterables = iters(tuple, count=3)
    iterator.api = MagicMock()
    results = []

    async def getiter(query, *args, **kwargs):
        iterator.api.api_iter(query, *args, **kwargs)
        for item in iterables:
            yield item

    iterator.api.getiter = getiter

    with patched as (m_inflate, ):
        async for result in iterator.__aiter__():
            results.append(result)

    assert results == [m_inflate.return_value] * len(iterables)
    assert (
        m_inflate.call_args_list
        == [[(result,), {}] for result in iterables])
    assert (
        iterator.api.api_iter.call_args
        == [('QUERY', ) + iterator.args, iterator.kwargs])


def test_abstract_iterator_count_request_headers(patches):
    iterator = DummyGithubIterator("API", "QUERY")
    iterator.api = MagicMock()
    patched = patches(
        "gidgethub",
        prefix="aio.api.github.abstract.iterator")

    with patched as (m_gidget, ):
        assert (
            iterator.count_request_headers
            == m_gidget.sansio.create_headers.return_value)

    assert (
        m_gidget.sansio.create_headers.call_args
        == [(iterator.api.requester, ),
            dict(accept=m_gidget.sansio.accept_format.return_value,
                 oauth_token=iterator.api.oauth_token)])
    assert (
        m_gidget.sansio.accept_format.call_args
        == [(), {}])
    assert (
        m_gidget.sansio.create_headers.return_value.__setitem__.call_args
        == [("content-length", "0"), {}])


def test_abstract_iterator_count_url(patches):
    iterator = DummyGithubIterator(MagicMock(), "QUERY")
    patched = patches(
        "gidgethub",
        prefix="aio.api.github.abstract.iterator")

    with patched as (m_gidget, ):
        assert (
            iterator.count_url
            == m_gidget.sansio.format_url.return_value)

    assert (
        m_gidget.sansio.format_url.call_args
        == [("QUERY&per_page=1", {}),
            dict(base_url=iterator.api.base_url)])

    assert "count_url" not in iterator.__dict__


@pytest.mark.parametrize("rate_limit", [None] + list(range(0, 6)))
async def test_abstract_iterator_total_count(patches, rate_limit):
    iterator = DummyGithubIterator(MagicMock(), "QUERY")
    patched = patches(
        "AGithubIterator.count_from_response",
        ("AGithubIterator.count_request_headers",
         dict(new_callable=PropertyMock)),
        ("AGithubIterator.count_url",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.iterator")
    iterator.api._request = AsyncMock()
    if rate_limit is None:
        iterator.api.rate_limit = rate_limit
    else:
        iterator.api.rate_limit.remaining = rate_limit

    with patched as (m_count, m_headers, m_url):
        assert await iterator.total_count == m_count.return_value

    if rate_limit is not None:
        assert iterator.api.rate_limit.remaining == (rate_limit - 1)
    assert (
        m_count.call_args
        == [(iterator.api._request.return_value, ), {}])
    assert (
        iterator.api._request.call_args
        == [("GET", m_url.return_value, m_headers.return_value, b""), {}])
    assert (
        "total_count"
        in getattr(iterator, github.AGithubIterator.total_count.cache_name))


@pytest.mark.parametrize(
    "data",
    [{}, dict(foo="bar"), dict(bar="baz", total_count="23")])
def test_abstract_iterator_count_from_data(patches, data):
    iterator = DummyGithubIterator("API", "QUERY")
    patched = patches(
        "int",
        prefix="aio.api.github.abstract.iterator")

    with patched as (m_int, ):
        assert (
            iterator.count_from_data(data)
            == (m_int.return_value
                if "total_count" in data
                else 0))

    if "total_count" not in data:
        assert not m_int.called
        return
    assert (
        m_int.call_args
        == [(data["total_count"], ), {}])


@pytest.mark.parametrize(
    "headers",
    [{}, dict(foo="bar"), dict(bar="baz", Link=MagicMock())])
def test_abstract_iterator_count_from_headers(patches, headers):
    iterator = DummyGithubIterator(MagicMock(), "QUERY")
    patched = patches(
        "int",
        prefix="aio.api.github.abstract.iterator")

    with patched as (m_int, ):
        assert (
            iterator.count_from_headers(headers)
            == (m_int.return_value
                if "Link" in headers
                else 0))

    if "Link" not in headers:
        assert not m_int.called
        return
    assert (
        m_int.call_args
        == [(headers["Link"].split.return_value
                            .__getitem__.return_value
                            .split.return_value
                            .__getitem__.return_value
                            .split.return_value
                            .__getitem__.return_value, ), {}])

    assert (
        headers["Link"].split.call_args
        == [(",", ), {}])
    assert (
        (headers["Link"].split.return_value
                        .__getitem__.call_args)
        == [(1, ), {}])
    assert (
        (headers["Link"].split.return_value
                        .__getitem__.return_value
                        .split.call_args)
        == [(">", ), {}])
    assert (
        (headers["Link"].split.return_value
                        .__getitem__.return_value
                        .split.return_value
                        .__getitem__.call_args)
        == [(0, ), {}])
    assert (
        (headers["Link"].split.return_value
                        .__getitem__.return_value
                        .split.return_value
                        .__getitem__.return_value
                        .split.call_args)
        == [("=", ), {}])
    assert (
        (headers["Link"].split.return_value
                        .__getitem__.return_value
                        .split.return_value
                        .__getitem__.return_value
                        .split.return_value
                        .__getitem__.call_args)
        == [(-1, ), {}])


@pytest.mark.parametrize("header", [None, True])
@pytest.mark.parametrize("data", [False, True])
@pytest.mark.parametrize("code", [200, 300, 400])
def test_abstract_iterator_count_from_response(patches, header, data, code):
    iterator = DummyGithubIterator(MagicMock(), "QUERY")
    patched = patches(
        "gidgethub",
        "AGithubIterator.count_from_data",
        "AGithubIterator.count_from_headers",
        prefix="aio.api.github.abstract.iterator")

    if header:
        response = [code, dict(Link=MagicMock()), "DATA"]
    else:
        response = [code, {}, "DATA"]

    with patched as (m_gidgethub, m_data, m_headers):
        m_gidgethub.sansio.decipher_response.return_value = (
            data and dict(total_count=23) or {}, 73, "XX")
        if code != 200:
            m_gidgethub.sansio.decipher_response.side_effect = (
                gidgethub.GitHubException("BOOM"))

            with pytest.raises(gidgethub.GitHubException):
                iterator.count_from_response(response)
        else:
            assert (
                iterator.count_from_response(response)
                == (m_headers.return_value
                    if response[1]
                    else m_data.return_value))

    assert (
        m_gidgethub.sansio.decipher_response.call_args
        == [tuple(response), {}])

    if code != 200:
        assert iterator.api.rate_limit != 73
        assert not m_headers.called
        assert not m_data.called
        return
    assert iterator.api.rate_limit == 73
    if response[1]:
        assert (
            m_headers.call_args
            == [(response[1], ), {}])
        assert not m_data.called
        return
    assert not m_headers.called
    assert (
        m_data.call_args
        == [(data and dict(total_count=23) or {}, ), {}])


@pytest.mark.parametrize("inflate", [True, False])
def test_abstract_iterator_inflate(inflate):
    iterator = DummyGithubIterator(MagicMock(), "QUERY")
    result = MagicMock()

    if inflate:
        iterator._inflate = MagicMock()

    assert (
        iterator.inflate(result)
        == (iterator._inflate.return_value
            if inflate
            else result))

    if not inflate:
        return

    assert (
        iterator._inflate.call_args
        == [(result, ), {}])
