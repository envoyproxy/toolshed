import importlib
import pathlib
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from envoy.base import utils


# this is necessary to fix coverage as these libs are imported before pytest
# is invoked
importlib.reload(utils)


def test_util_buffered_stdout():
    stdout = []

    with utils.buffered(stdout=stdout):
        print("test1")
        print("test2")
        sys.stdout.write("test3\n")
        sys.stderr.write("error0\n")

    assert stdout == ["test1", "test2", "test3"]


def test_util_buffered_stderr():
    stderr = []

    with utils.buffered(stderr=stderr):
        print("test1")
        print("test2")
        sys.stdout.write("test3\n")
        sys.stderr.write("error0\n")
        sys.stderr.write("error1\n")

    assert stderr == ["error0", "error1"]


def test_util_buffered_stdout_stderr():
    stdout = []
    stderr = []

    with utils.buffered(stdout=stdout, stderr=stderr):
        print("test1")
        print("test2")
        sys.stdout.write("test3\n")
        sys.stderr.write("error0\n")
        sys.stderr.write("error1\n")

    assert stdout == ["test1", "test2", "test3"]
    assert stderr == ["error0", "error1"]


def test_util_buffered_no_stdout_stderr():
    with pytest.raises(utils.BufferUtilError):
        with utils.buffered():
            pass


def test_util_nested():

    fun1_args = []
    fun2_args = []

    @contextmanager
    def fun1(arg):
        fun1_args.append(arg)
        yield "FUN1"

    @contextmanager
    def fun2(arg):
        fun2_args.append(arg)
        yield "FUN2"

    with utils.nested(fun1("A"), fun2("B")) as (fun1_yield, fun2_yield):
        assert fun1_yield == "FUN1"
        assert fun2_yield == "FUN2"

    assert fun1_args == ["A"]
    assert fun2_args == ["B"]


def test_util_coverage_with_data_file(patches):
    patched = patches(
        "ConfigParser",
        "tempfile.TemporaryDirectory",
        "os.path.join",
        "open",
        prefix="envoy.base.utils.utils")

    with patched as (m_config, m_tmp, m_join, m_open):
        with utils.coverage_with_data_file("PATH") as tmprc:
            assert tmprc == m_join.return_value
    assert (
        list(m_config.call_args)
        == [(), {}])
    assert (
        list(m_config.return_value.read.call_args)
        == [('.coveragerc',), {}])
    config_dict = m_config.return_value.__getitem__
    assert (
        list(config_dict.call_args)
        == [('run',), {}])
    assert (
        list(config_dict.return_value.__setitem__.call_args)
        == [('data_file', 'PATH'), {}])
    assert (
        list(m_tmp.call_args)
        == [(), {}])
    assert (
        list(m_join.call_args)
        == [(m_tmp.return_value.__enter__.return_value, '.coveragerc'), {}])
    assert (
        list(m_open.call_args)
        == [(m_join.return_value, 'w'), {}])
    assert (
        list(m_config.return_value.write.call_args)
        == [(m_open.return_value.__enter__.return_value,), {}])


@pytest.mark.parametrize(
    "tarballs",
    [(), tuple("TARB{i}" for i in range(0, 3))])
def test_util_extract(patches, tarballs):
    patched = patches(
        "nested",
        "pathlib",
        "tarfile.open",
        prefix="envoy.base.utils.utils")

    with patched as (m_nested, m_plib, m_open):
        _extractions = [MagicMock(), MagicMock()]
        m_nested.return_value.__enter__.return_value = _extractions

        if tarballs:
            assert utils.extract("PATH", *tarballs) == m_plib.Path.return_value
        else:
            with pytest.raises(utils.ExtractError) as e:
                utils.extract("PATH", *tarballs)

    if not tarballs:
        assert (
            e.value.args[0]
            == 'No tarballs specified for extraction to PATH')
        assert not m_nested.called
        assert not m_open.called
        for _extract in _extractions:
            assert not _extract.extractall.called
        return

    assert (
        list(m_plib.Path.call_args)
        == [("PATH", ), {}])

    for _extract in _extractions:
        assert (
            list(_extract.extractall.call_args)
            == [(), dict(path="PATH")])

    assert (
        list(m_open.call_args_list)
        == [[(tarb, ), {}] for tarb in tarballs])
    assert (
        list(m_nested.call_args)
        == [tuple(m_open.return_value for x in tarballs), {}])


@pytest.mark.parametrize(
    "tarballs",
    [(), tuple("TARB{i}" for i in range(0, 3))])
def test_util_untar(patches, tarballs):
    patched = patches(
        "tempfile.TemporaryDirectory",
        "extract",
        prefix="envoy.base.utils.utils")

    with patched as (m_tmp, m_extract):
        with utils.untar(*tarballs) as tmpdir:
            assert tmpdir == m_extract.return_value

    assert (
        list(m_tmp.call_args)
        == [(), {}])
    assert (
        list(m_extract.call_args)
        == [(m_tmp.return_value.__enter__.return_value, ) + tarballs, {}])


def test_util_from_yaml(patches):
    patched = patches(
        "pathlib",
        "yaml",
        prefix="envoy.base.utils.utils")

    with patched as (m_plib, m_yaml):
        assert utils.from_yaml("PATH") == m_yaml.safe_load.return_value

    assert (
        list(m_plib.Path.call_args)
        == [("PATH", ), {}])
    assert (
        list(m_yaml.safe_load.call_args)
        == [(m_plib.Path.return_value.read_text.return_value, ), {}])
    assert (
        list(m_plib.Path.return_value.read_text.call_args)
        == [(), {}])


def test_util_to_yaml(patches):
    patched = patches(
        "pathlib",
        "yaml",
        prefix="envoy.base.utils.utils")

    with patched as (m_plib, m_yaml):
        assert utils.to_yaml("DATA", "PATH") == m_plib.Path.return_value

    assert (
        list(m_yaml.dump.call_args)
        == [("DATA", ), {}])
    assert (
        list(m_plib.Path.return_value.write_text.call_args)
        == [(m_yaml.dump.return_value, ), {}])
    assert (
        list(m_plib.Path.call_args)
        == [("PATH", ), {}])


@pytest.mark.parametrize(
    "path",
    ["x.foo", "x.bar", "x.tar", "x.tar.xz", "x.xz"])
def test_is_tarlike(patches, path):
    matches = False
    for ext in utils.TAR_EXTS:
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


@pytest.mark.parametrize(
    "casted",
    [(), [], False, None, "", "X", ["Y"]])
def test_typed(patches, casted):
    patched = patches(
        "trycast",
        "ellipsize",
        prefix="envoy.base.utils.utils")

    class DummyValue:

        def __str__(self):
            return "VALUE"

    value = DummyValue()

    with patched as (m_try, m_elips):
        m_try.return_value = casted

        if casted is None:
            with pytest.raises(utils.TypeCastingError) as e:
                utils.typed("TYPE", value)

            assert (
                e.value.args[0]
                == ("Value has wrong type or shape for Type "
                    f"TYPE: {m_elips.return_value}"))
            assert (
                list(m_elips.call_args)
                == [("VALUE", 10), {}])
        else:
            assert utils.typed("TYPE", value) == value
            assert not m_elips.called

    assert (
        list(m_try.call_args)
        == [("TYPE", value), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("filter", [True, False])
async def test_async_list(filter):

    async def async_generator():
        for x in range(0, 20):
            yield x

    kwargs = (
        dict(filter=lambda x: ((x % 2) and x))
        if filter
        else {})
    expected = (
        [x for x in range(0, 20) if (x % 2)]
        if filter
        else list(range(0, 20)))
    assert (
        await utils.async_list(async_generator(), **kwargs)
        == expected)


@pytest.mark.parametrize("path", ["/tmp", pathlib.Path("/tmp")])
def test_cd_and_return(path):
    cwd = pathlib.Path.cwd()

    with utils.cd_and_return(path):
        assert pathlib.Path.cwd() != cwd
        assert pathlib.Path.cwd() == pathlib.Path("/tmp")

    assert pathlib.Path.cwd() == cwd


@pytest.mark.parametrize("data", [b"BYTES", "STRING"])
def test_to_bytes(data):
    assert (
        utils.to_bytes(data)
        == (data.encode("utf-8")
            if not isinstance(data, bytes)
            else data))
