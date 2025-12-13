
from unittest.mock import MagicMock

from aio.api import github


def test_utils_dt_from_js_isoformat(patches):
    patched = patches(
        "datetime",
        prefix="aio.api.github.utils")
    iso = MagicMock()

    with patched as (m_dt, ):
        assert (
            github.utils.dt_from_js_isoformat(iso)
            == m_dt.fromisoformat.return_value)

    assert (
        m_dt.fromisoformat.call_args
        == [(iso.replace.return_value, ), {}])
    assert (
        iso.replace.call_args
        == [("Z", "+00:00"), {}])


def test_utils_dt_to_js_isoformat():
    dt = MagicMock()
    assert (
        github.utils.dt_to_js_isoformat(dt)
        == dt.isoformat.return_value.replace.return_value)
    assert (
        dt.isoformat.call_args
        == [(), {}])
    assert (
        dt.isoformat.return_value.replace.call_args
        == [("+00:00", "Z"), {}])
