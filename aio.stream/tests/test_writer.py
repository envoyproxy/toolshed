
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio import stream


def test_stream_writer_constructor(patches):
    args = [f"ARG{i}" for i in range(0, 3)]
    kwargs = dict(foo="FOO", bar="BAR")
    patched = patches(
        "AsyncStream.__init__",
        prefix="aio.stream._writer")

    with patched as (m_super, ):
        m_super.return_value = None
        writer = stream.Writer(*args, **kwargs)

    assert isinstance(writer, stream.AsyncStream)
    assert (
        list(m_super.call_args)
        == [tuple(args), kwargs])


async def test_stream_writer_stream_bytes(patches):
    writer = stream.Writer("BUFFER")
    response = MagicMock()
    patched = patches(
        ("Writer.buffer", dict(new_callable=PropertyMock)),
        ("Writer.chunk_size", dict(new_callable=PropertyMock)),
        prefix="aio.stream._writer")

    class DummyChunker:

        async def iter_chunked(self, chunk_size):
            for i in range(0, 3):
                yield f"CHUNK{i}"

    _chunker = DummyChunker()
    response.content.iter_chunked.side_effect = _chunker.iter_chunked

    with patched as (m_buffer, m_size):
        m_buffer.return_value.write = AsyncMock()
        assert not await writer.stream_bytes(response)

    assert (
        list(response.content.iter_chunked.call_args)
        == [(m_size.return_value, ), {}])
    assert (
        list(list(c) for c in m_buffer.return_value.write.call_args_list)
        == [[(f'CHUNK{i}',), {}] for i in range(0, 3)])


@pytest.mark.parametrize("chunk_size", [None, 0, 23])
async def test_stream_writer(patches, chunk_size):
    patched = patches(
        "aiofiles",
        "Writer",
        prefix="aio.stream._writer")
    args = ((chunk_size, ) if chunk_size is not None else ())

    with patched as (m_aiofiles, m_writer):
        async with stream.writer("PATH", *args) as writer:
            pass

    assert writer == m_writer.return_value
    assert (
        list(m_aiofiles.open.call_args)
        == [("PATH", 'wb'), {}])
    assert (
        list(m_writer.call_args)
        == [(m_aiofiles.open.return_value.__aenter__.return_value,),
            {'chunk_size': chunk_size}])
