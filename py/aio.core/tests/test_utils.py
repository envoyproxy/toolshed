
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
        prefix="aio.core.utils.context")
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
        prefix="aio.core.utils.context")
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
        prefix="aio.core.utils.context")
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


@pytest.mark.parametrize(
    "tarballs",
    [(), tuple("TARB{i}" for i in range(0, 3))])
def test_util_extract(patches, tarballs):
    patched = patches(
        "functional",
        "pathlib",
        "tarfile.open",
        prefix="aio.core.utils.data")

    with patched as (m_fun, m_plib, m_open):
        _extractions = [MagicMock(), MagicMock()]
        m_fun.nested.return_value.__enter__.return_value = _extractions

        if tarballs:
            assert utils.extract("PATH", *tarballs) == m_plib.Path.return_value
        else:
            with pytest.raises(utils.ExtractError) as e:
                utils.extract("PATH", *tarballs)

    if not tarballs:
        assert (
            e.value.args[0]
            == 'No tarballs specified for extraction to PATH')
        assert not m_fun.nested.called
        assert not m_open.called
        for _extract in _extractions:
            assert not _extract.extractall.called
        return

    assert (
        m_plib.Path.call_args
        == [("PATH", ), {}])

    for _extract in _extractions:
        assert (
            _extract.extractall.call_args
            == [(), dict(path="PATH")])

    assert (
        m_open.call_args_list
        == [[(tarb, ), {}] for tarb in tarballs])
    assert (
        m_fun.nested.call_args
        == [tuple(m_open.return_value for x in tarballs), {}])


@pytest.mark.parametrize("type", [None, False, "TYPE"])
def test_util_from_json(patches, type):
    args = (
        (type, )
        if type is not None
        else ())
    patched = patches(
        "pathlib",
        "json",
        "functional",
        prefix="aio.core.utils.data")

    with patched as (m_plib, m_json, m_func):
        assert (
            utils.from_json("PATH", *args)
            == (m_json.loads.return_value
                if type is None
                else m_func.utils.typed.return_value))

    if type is None:
        assert not m_func.utils.typed.called
    else:
        assert (
            m_func.utils.typed.call_args
            == [(type, m_json.loads.return_value, ), {}])
    assert (
        m_plib.Path.call_args
        == [("PATH", ), {}])
    assert (
        m_json.loads.call_args
        == [(m_plib.Path.return_value.read_text.return_value, ), {}])
    assert (
        m_plib.Path.return_value.read_text.call_args
        == [(), {}])


@pytest.mark.parametrize("type", [None, False, "TYPE"])
def test_util_from_yaml(patches, type):
    args = (
        (type, )
        if type is not None
        else ())
    patched = patches(
        "pathlib",
        "yaml",
        "functional",
        prefix="aio.core.utils.data")

    with patched as (m_plib, m_yaml, m_func):
        assert (
            utils.from_yaml("PATH", *args)
            == (m_yaml.safe_load.return_value
                if type is None
                else m_func.utils.typed.return_value))

    if type is None:
        assert not m_func.utils.typed.called
    else:
        assert (
            m_func.utils.typed.call_args
            == [(type, m_yaml.safe_load.return_value, ), {}])
    assert (
        m_plib.Path.call_args
        == [("PATH", ), {}])
    assert (
        m_yaml.safe_load.call_args
        == [(m_plib.Path.return_value.read_text.return_value, ), {}])
    assert (
        m_plib.Path.return_value.read_text.call_args
        == [(), {}])


@pytest.mark.parametrize("length", [0, 10, 20, 30, 40, 50])
@pytest.mark.parametrize("raises", [None, ValueError, Exception])
def test_is_sha(patches, length, raises):
    text = MagicMock()
    text.__len__.return_value = length
    patched = patches(
        "int",
        prefix="aio.core.utils.data")
    _do_int = int

    def _int(item, base=None):
        if base == 16 and raises:
            raise raises()
        return _do_int(item)

    with patched as (m_int, ):
        m_int.side_effect = _int
        if length == 40 and raises == Exception:
            with pytest.raises(Exception):
                utils.is_sha(text)
        else:
            assert (
                utils.is_sha(text)
                == (length == 40
                    and not raises))
    if length == 40:
        assert (
            m_int.call_args
            == [(text, 16), {}])
    else:
        assert not m_int.called


def test_util_to_yaml(patches):
    patched = patches(
        "pathlib",
        "yaml",
        prefix="aio.core.utils.data")

    with patched as (m_plib, m_yaml):
        assert utils.to_yaml("DATA", "PATH") == m_plib.Path.return_value

    assert (
        m_yaml.dump.call_args
        == [("DATA", ), {}])
    assert (
        m_plib.Path.return_value.write_text.call_args
        == [(m_yaml.dump.return_value, ), {}])
    assert (
        m_plib.Path.call_args
        == [("PATH", ), {}])


@pytest.mark.parametrize(
    "path",
    ["x.foo", "x.bar", "x.tar", "x.tar.xz", "x.xz"])
def test_is_tarlike(patches, path):
    matches = False
    for ext in utils.data.TAR_EXTS:
        if path.endswith(ext):
            matches = True
            break
    assert utils.is_tarlike(path) == matches


@pytest.mark.parametrize("text_length", range(0, 10))
@pytest.mark.parametrize("max_length", range(5, 15))
def test_ellipsize(text_length, max_length):
    expected = (
        "X" * text_length
        if text_length <= max_length
        else "{text}...".format(text="X" * (max_length - 3)))
    assert (
        utils.ellipsize("X" * text_length, max_length)
        == expected)
