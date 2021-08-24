
import pytest

from aio import stream


@pytest.mark.parametrize("chunk_size", [None, 0, 23])
def test_stream_constructor(chunk_size):
    kwargs = dict(chunk_size=chunk_size) if chunk_size is not None else {}
    base = stream.AsyncStream("BUFFER", **kwargs)
    assert base._buffer == "BUFFER"
    assert base._chunk_size == chunk_size
    assert base.default_chunk_size == 1024 * 16
    assert base.buffer == base._buffer
    assert "buffer" not in base.__dict__
    assert base.chunk_size == base._chunk_size or base.default_chunk_size
    assert "chunk_size" not in base.__dict__
