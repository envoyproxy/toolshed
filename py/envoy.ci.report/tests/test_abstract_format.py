
from unittest.mock import MagicMock

import pytest

from envoy.ci import report


class DummyFormat(report.abstract.AFormat):

    def out(self, data):
        data.out_called()


def test_format_constructor():
    with pytest.raises(TypeError):
        report.abstract.AFormat()
    DummyFormat()


def test_format_out():
    format = DummyFormat()
    with pytest.raises(NotImplementedError):
        report.abstract.AFormat.out(format, "DATA")
    data = MagicMock()
    format(data)
    assert (
        data.out_called.call_args
        == [(), {}])


def test_jsonformat_constructor():
    format = report.abstract.AJSONFormat()
    assert isinstance(format, report.interface.IFormat)


def test_jsonformat_out(patches):
    format = report.abstract.AJSONFormat()
    data = MagicMock()
    patched = patches(
        "json",
        "print",
        prefix="envoy.ci.report.abstract.format")

    with patched as (m_json, m_print):
        assert not format(data)

    assert (
        m_print.call_args
        == [(m_json.dumps.return_value, ), {}])
    assert (
        m_json.dumps.call_args
        == [(data, ), {}])


def test_markdownformat_constructor():
    format = report.abstract.AMarkdownFormat()
    assert isinstance(format, report.interface.IFormat)


def test_markdownformat_out(patches, iters):
    format = report.abstract.AMarkdownFormat()
    data = MagicMock()
    patched = patches(
        "AMarkdownFormat._handle_commit",
        prefix="envoy.ci.report.abstract.format")
    data.items.return_value = iters(dict).items()

    with patched as (m_handle, ):
        assert not format(data)

    assert (
        m_handle.call_args_list
        == [[item, {}]
            for item
            in data.items.return_value])
