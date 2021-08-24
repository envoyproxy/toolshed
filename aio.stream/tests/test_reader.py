
from unittest.mock import MagicMock, PropertyMock

import pytest

from aio import stream


@pytest.mark.parametrize("size", [None, 0, 23])
def test_stream_reader_constructor(patches, size):
    args = [f"ARG{i}" for i in range(0, 3)]
    kwargs = dict(foo="FOO", bar="BAR")
    kwargs.update(dict(size=size) if size is not None else {})
    patched = patches(
        "AsyncStream.__init__",
        prefix="aio.stream._reader")

    with patched as (m_super, ):
        m_super.return_value = None
        reader = stream.Reader(*args, **kwargs)

    kwargs.pop("size", None)
    assert (
        list(m_super.call_args)
        == [tuple(args), kwargs])
    assert reader._size == size
    assert reader.size == size
    assert "size" not in reader.__dict__


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [None, 0, 23])
async def test_stream_reader_dunder_aiter(patches, size):
    reader = stream.Reader("BUFFER")
    patched = patches(
        ("Reader.chunk_size", dict(new_callable=PropertyMock)),
        ("Reader.buffer", dict(new_callable=PropertyMock)),
        prefix="aio.stream._reader")

    class DummyChunker:
        counter = 0
        _read = MagicMock()

        async def read(self, chunk_size=None):
            self._read(chunk_size)
            if self.counter < 3:
                self.counter += 1
                return f"CHUNK{self.counter - 1}"

    _chunker = DummyChunker()
    results = []

    with patched as (m_size, m_buffer):
        m_buffer.return_value.read = _chunker.read
        async for result in reader:
            results.append(result)

    assert (
        results
        == [f"CHUNK{i}" for i in range(0, 3)])
    assert (
        list(list(c) for c in _chunker._read.call_args_list)
        == [[(m_size.return_value, ), {}] for i in range(0, 4)])


@pytest.mark.parametrize("size", [None, 0, 23])
def test_stream_reader_dunder_len(patches, size):
    reader = stream.Reader("BUFFER")
    patched = patches(
        ("Reader.size", dict(new_callable=PropertyMock)),
        prefix="aio.stream._reader")

    with patched as (m_size, ):
        m_size.return_value = size
        if size is None:
            with pytest.raises(TypeError) as e:
                len(reader)
        else:
            assert len(reader) == size

    if size is None:
        assert (
            e.value.args[0]
            == "object of type 'Reader' with no 'size' cannot get len()")


@pytest.mark.asyncio
@pytest.mark.parametrize("chunk_size", [None, 0, 23])
async def test_stream_reader(patches, chunk_size):
    patched = patches(
        "pathlib",
        "aiofiles",
        "Reader",
        prefix="aio.stream._reader")
    args = ((chunk_size, ) if chunk_size is not None else ())

    with patched as (m_plib, m_aiofiles, m_reader):
        async with stream.reader("PATH", *args) as reader:
            pass

    assert reader == m_reader.return_value
    assert (
        list(m_plib.Path.call_args)
        == [("PATH", ), {}])
    assert (
        list(m_aiofiles.open.call_args)
        == [(m_plib.Path.return_value, 'rb'), {}])
    assert (
        list(m_reader.call_args)
        == [(m_aiofiles.open.return_value.__aenter__.return_value,),
            {'chunk_size': chunk_size,
             'size': m_plib.Path.return_value.stat.return_value.st_size}])
    assert (
        list(m_plib.Path.return_value.stat.call_args)
        == [(), {}])
