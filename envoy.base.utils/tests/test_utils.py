import importlib
import pathlib
from unittest.mock import MagicMock

import pytest

from envoy.base import utils


# this is necessary to fix coverage as these libs are imported before pytest
# is invoked
importlib.reload(utils)


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
        m_config.call_args
        == [(), {}])
    assert (
        m_config.return_value.read.call_args
        == [('.coveragerc',), {}])
    config_dict = m_config.return_value.__getitem__
    assert (
        config_dict.call_args
        == [('run',), {}])
    assert (
        config_dict.return_value.__setitem__.call_args
        == [('data_file', 'PATH'), {}])
    assert (
        m_tmp.call_args
        == [(), {}])
    assert (
        m_join.call_args
        == [(m_tmp.return_value.__enter__.return_value, '.coveragerc'), {}])
    assert (
        m_open.call_args
        == [(m_join.return_value, 'w'), {}])
    assert (
        m_config.return_value.write.call_args
        == [(m_open.return_value.__enter__.return_value,), {}])


@pytest.mark.parametrize(
    "tarballs",
    [(), tuple("TARB{i}" for i in range(0, 3))])
def test_util_extract(patches, tarballs):
    patched = patches(
        "functional",
        "pathlib",
        "tarfile.open",
        prefix="envoy.base.utils.utils")

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
        m_tmp.call_args
        == [(), {}])
    assert (
        m_extract.call_args
        == [(m_tmp.return_value.__enter__.return_value, ) + tarballs, {}])


@pytest.mark.parametrize("type", [None, False, "TYPE"])
def test_util_from_yaml(patches, type):
    args = (
        (type, )
        if type is not None
        else ())
    patched = patches(
        "pathlib",
        "yaml",
        "typed",
        prefix="envoy.base.utils.utils")

    with patched as (m_plib, m_yaml, m_typed):
        assert (
            utils.from_yaml("PATH", *args)
            == (m_yaml.safe_load.return_value
                if type is None
                else m_typed.return_value))

    if type is None:
        assert not m_typed.called
    else:
        assert (
            m_typed.call_args
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


def test_util_to_yaml(patches):
    patched = patches(
        "pathlib",
        "yaml",
        prefix="envoy.base.utils.utils")

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
                m_elips.call_args
                == [("VALUE", 10), {}])
        else:
            assert utils.typed("TYPE", value) == value
            assert not m_elips.called

    assert (
        m_try.call_args
        == [("TYPE", value), {}])


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


@pytest.mark.parametrize("length", [0, 10, 20, 30, 40, 50])
@pytest.mark.parametrize("raises", [None, ValueError, Exception])
def test_is_sha(patches, length, raises):
    text = MagicMock()
    text.__len__.return_value = length
    patched = patches(
        "int",
        prefix="envoy.base.utils.utils")
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


@pytest.mark.parametrize("mode", [None, "r", "w"])
@pytest.mark.parametrize(
    "path",
    ["foo", "foo.tar", "foo.tar.gz", "foo.tar.xz", "foo.tar.bz2"])
def test_tar_mode(mode, path):
    m_path = MagicMock()
    m_path.__str__.return_value = path
    expected = mode or "r"
    suffixes = ["gz", "bz2", "xz"]
    for suffix in suffixes:
        if str(path).endswith(f".{suffix}"):
            expected = f"{mode or 'r'}:{suffix}"
            break
    kwargs = {}
    if mode:
        kwargs["mode"] = mode
    assert (
        utils.tar_mode(m_path, **kwargs)
        == expected)


def test_dt_to_utc_isoformat(patches):
    patched = patches(
        "pytz",
        prefix="envoy.base.utils.utils")
    dt = MagicMock()

    with patched as (m_pytz, ):
        assert (
            utils.dt_to_utc_isoformat(dt)
            == (dt.replace.return_value.date
                .return_value.isoformat.return_value))

    assert (
        dt.replace.call_args
        == [(), dict(tzinfo=m_pytz.UTC)])
    assert (
        dt.replace.return_value.date.call_args
        == [(), {}])
    assert (
        dt.replace.return_value.date.return_value.isoformat.call_args
        == [(), {}])


@pytest.mark.parametrize("n", [None] + list(range(1, 5)))
def test_last_n_bytes_of(patches, n):
    patched = patches(
        "open",
        "os",
        prefix="envoy.base.utils.utils")
    target = MagicMock()
    args = (
        (n, )
        if n is not None
        else ())

    with patched as (m_open, m_os):
        m_open.return_value.__enter__.return_value.tell.return_value = 23
        assert (
            utils.last_n_bytes_of(target, *args)
            == m_open.return_value.__enter__.return_value.read.return_value)

    assert (
        m_open.call_args
        == [(target, "rb"), {}])
    assert (
        m_open.return_value.__enter__.return_value.seek.call_args_list
        == [[(0, m_os.SEEK_END), {}],
            [(23 - (n or 1), ), {}]])
    assert (
        m_open.return_value.__enter__.return_value.tell.call_args
        == [(), {}])
    assert (
        m_open.return_value.__enter__.return_value.read.call_args
        == [(n or 1, ), {}])


def test_minor_version_for(patches):
    patched = patches(
        "_version",
        prefix="envoy.base.utils.utils")
    version = MagicMock()

    with patched as (m_version, ):
        assert (
            utils.minor_version_for(version)
            == m_version.Version.return_value)

    assert (
        m_version.Version.call_args
        == [(f"{version.major}.{version.minor}", ), {}])


@pytest.mark.parametrize("patch", [None, True, False])
def test_increment_version(patches, patch):
    args = (
        (patch, )
        if patch is not None
        else ())
    patched = patches(
        "_version",
        prefix="envoy.base.utils.utils")
    version = MagicMock()
    version.minor = 7
    version.micro = 23
    expected = (
        f"{version.major}.8.23"
        if not patch
        else f"{version.major}.7.24")

    with patched as (m_version, ):
        assert (
            utils.increment_version(version, *args)
            == m_version.Version.return_value)

    assert (
        m_version.Version.call_args
        == [(expected, ), {}])
