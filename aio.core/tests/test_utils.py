
import contextlib
from unittest.mock import MagicMock, PropertyMock

import pytest

from aio.core import utils


def test_captured_constructor():
    captured = utils.Captured()
    assert captured.result is None
    assert captured.warnings == ()


@pytest.mark.parametrize("result", [True, False, str])
@pytest.mark.parametrize("warnings", [True, str])
def test_captured_dunder_str(patches, result, warnings):
    captured = utils.Captured()
    patched = patches(
        ("Captured._warning_str",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.utils")
    if result == str:
        captured.result = " RESULT  "
    elif result:
        captured.result = MagicMock()
    warnings = (
        " WARNINGS  "
        if warnings == str
        else MagicMock())

    with patched as (m_warn, ):
        m_warn.return_value = warnings
        assert (
            str(captured)
            == f"{warnings}\n{captured.result or ''}".strip())


def test_captured__warning_str(iters, patches):
    captured = utils.Captured()
    patched = patches(
        "str",
        prefix="aio.core.utils")
    captured.warnings = iters(cb=lambda i: MagicMock())

    with patched as (m_str, ):
        m_str.side_effect = lambda x: f"  {x}  "
        assert (
            captured._warning_str
            == "\n".join(
                f"  {w.message}  "
                for w
                in captured.warnings).strip())

    assert (
        m_str.call_args_list
        == [[(w.message, ), {}]
            for w in captured.warnings])

    assert "_warning_str" not in captured.__dict__


def test_captured__warnings(patches):
    patched = patches(
        "Captured",
        "_warnings",
        prefix="aio.core.utils")
    w = MagicMock()
    cap = MagicMock()

    @contextlib.contextmanager
    def capture(**kwargs):
        yield w

    with patched as (m_capture, m_warn):
        m_capture.return_value = cap
        m_warn.catch_warnings.side_effect = capture

        with utils.captured_warnings() as yielded:
            pass

    assert yielded == cap
    assert yielded.warnings == w
    assert (
        m_warn.catch_warnings.call_args
        == [(), dict(record=True)])
