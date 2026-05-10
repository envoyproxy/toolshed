from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.github.release.stream import _reader, _writer
from envoy.github.release.stream.base import AsyncStream
from envoy.github.release.stream._reader import Reader
from envoy.github.release.stream._writer import Writer


@pytest.mark.parametrize("chunk_size", [None, 4096])
def test_stream_constructor(chunk_size):
    stream = AsyncStream("BUFFER", chunk_size=chunk_size)
    assert stream.buffer == "BUFFER"
    assert (
        stream.chunk_size
        == (chunk_size
            if chunk_size is not None
            else 1024 * 16))


@pytest.mark.parametrize("size", [None, 123])
def test_reader_constructor(size):
    reader = Reader("BUFFER", size=size)
    assert reader.buffer == "BUFFER"
    assert reader.size == size


async def test_reader_dunder_aiter(patches):
    stream = Reader("BUFFER")
    patched = patches(
        ("Reader.buffer", dict(new_callable=PropertyMock)),
        ("Reader.chunk_size", dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.stream._reader")
    chunks = [f"CHUNK{i}".encode() for i in range(0, 3)]

    with patched as (m_buffer, m_chunk_size):
        m_chunk_size.return_value = 32
        m_buffer.return_value.read = AsyncMock(
            side_effect=[*chunks, b""])
        result = [chunk async for chunk in stream]

    assert result == chunks
    assert (
        m_buffer.return_value.read.call_args_list
        == [[(32, ), {}]] * 4)


@pytest.mark.parametrize("size", [None, 123])
def test_reader_dunder_len(patches, size):
    stream = Reader("BUFFER")
    patched = patches(
        ("Reader.size", dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.stream._reader")

    with patched as (m_size, ):
        m_size.return_value = size
        if size is None:
            with pytest.raises(TypeError) as e:
                len(stream)
            assert (
                e.value.args[0]
                == "object of type 'Reader' with no 'size' cannot get len()")
        else:
            assert len(stream) == size


async def test_reader(patches):
    patched = patches(
        "aiofiles",
        "pathlib",
        "Reader",
        prefix="envoy.github.release.stream._reader")

    with patched as (m_aiofiles, m_pathlib, m_reader):
        m_aiofiles.open.return_value.__aenter__ = AsyncMock(
            return_value="BUFFER")
        m_aiofiles.open.return_value.__aexit__ = AsyncMock(return_value=None)
        m_pathlib.Path.return_value.stat.return_value.st_size = 456
        async with _reader.reader("PATH", chunk_size=4096) as stream:
            assert stream == m_reader.return_value

    assert (
        m_pathlib.Path.call_args
        == [("PATH", ), {}])
    assert (
        m_aiofiles.open.call_args
        == [(m_pathlib.Path.return_value, "rb"), {}])
    assert (
        m_reader.call_args
        == [("BUFFER", ),
            dict(chunk_size=4096, size=456)])


async def test_writer_stream_bytes(patches):
    writer = Writer("BUFFER")
    patched = patches(
        ("Writer.buffer", dict(new_callable=PropertyMock)),
        ("Writer.chunk_size", dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.stream._writer")
    chunks = [f"CHUNK{i}".encode() for i in range(0, 3)]
    response = MagicMock()

    async def iter_chunks(*args):
        for chunk in chunks:
            yield chunk

    response.content.iter_chunked.side_effect = iter_chunks
    with patched as (m_buffer, m_chunk_size):
        m_chunk_size.return_value = 32
        m_buffer.return_value.write = AsyncMock()
        await writer.stream_bytes(response)

    assert (
        response.content.iter_chunked.call_args
        == [(32, ), {}])
    assert (
        m_buffer.return_value.write.call_args_list
        == [[(chunk, ), {}] for chunk in chunks])


async def test_writer(patches):
    patched = patches(
        "aiofiles",
        "Writer",
        prefix="envoy.github.release.stream._writer")

    with patched as (m_aiofiles, m_writer):
        m_aiofiles.open.return_value.__aenter__ = AsyncMock(
            return_value="BUFFER")
        m_aiofiles.open.return_value.__aexit__ = AsyncMock(return_value=None)
        async with _writer.writer("PATH", chunk_size=4096) as stream:
            assert stream == m_writer.return_value

    assert (
        m_aiofiles.open.call_args
        == [("PATH", "wb"), {}])
    assert (
        m_writer.call_args
        == [("BUFFER", ), dict(chunk_size=4096)])
