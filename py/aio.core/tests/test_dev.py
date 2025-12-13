
from unittest.mock import MagicMock

import pytest

from aio.core import dev


@pytest.mark.parametrize(
    "args", [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{},
     {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_dev_timing(patches, args, kwargs):
    patched = patches(
        "time",
        "print",
        prefix="aio.core.dev.perf")

    wrapped_fun = MagicMock()

    def some_fun(*args, **kwargs):
        wrapped_fun(*args, **kwargs)
        return "FUN ALL ROUND"

    with patched as (m_time, m_print):
        assert (
            dev.timing(some_fun)(*args, **kwargs)
            == "FUN ALL ROUND")

    # TODO: check order
    assert (
        wrapped_fun.call_args
        == [tuple(args), kwargs])
    time_taken = (
        m_time.perf_counter.return_value
              .__sub__.return_value.__round__.return_value)
    assert (
        m_print.call_args
        == [(f"Finished 'some_fun' in {time_taken} secs", ), {}])
