
import gzip
from types import GeneratorType
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import aiohttp

import abstracts

from envoy.dependency import check


@abstracts.implementer(check.ADependencyCVEs)
class DummyDependencyCVEs:

    @property
    def cpe_class(self):
        return super().cpe_class

    @property
    def cve_class(self):
        return super().cve_class

    @property
    def ignored_cves(self):
        return super().ignored_cves


@pytest.mark.parametrize("config_path", [None, "", "PATH"])
@pytest.mark.parametrize("session", [None, "", "SESSION"])
def test_cves_constructor(patches, config_path, session):
    kwargs = {}
    if config_path is not None:
        kwargs["config_path"] = config_path
    if session is not None:
        kwargs["session"] = session

    with pytest.raises(TypeError):
        check.ADependencyCVEs("DEPENDENCIES", **kwargs)

    cves = DummyDependencyCVEs("DEPENDENCIES", **kwargs)
    assert cves.dependencies == "DEPENDENCIES"
    assert cves._config_path == config_path
    assert cves._session == session

    with pytest.raises(NotImplementedError):
        cves.cpe_class
    with pytest.raises(NotImplementedError):
        cves.cve_class

    assert cves.cves == {}
    assert "cves" in cves.__dict__
    assert (
        cves.nist_url_tpl
        == check.abstract.cves.cves.NIST_URL_TPL)
    assert "nist_url_tpl" not in cves.__dict__
    assert (
        cves.start_year
        == check.abstract.cves.cves.SCAN_FROM_YEAR)
    assert "start_year" not in cves.__dict__


@pytest.mark.parametrize("config_path", [None, "", "PATH"])
@pytest.mark.parametrize("start_year", [None, "", 0, 1, 7, 23])
def test_cves_config(patches, config_path, start_year):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "dict",
        ("ADependencyCVEs.config_path", dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.user_config", dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.nist_url_tpl", dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.start_year", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_dict, m_path, m_user_config, m_tpl, m_start):
        m_dict.return_value.__getitem__.return_value = start_year
        if start_year == 0:
            with pytest.raises(check.exceptions.CVECheckError) as e:
                cves.config
            assert (
                e.value.args[0]
                == ("`start_year` must be specified in config "
                    f"({m_path.return_value}) or implemented "
                    "by `DummyDependencyCVEs`"))
        else:
            assert cves.config == m_dict.return_value

    assert (
        m_dict.call_args
        == [(),
            dict(nist_url=m_tpl.return_value,
                 start_year=m_start.return_value)])
    assert (
        m_dict.return_value.update.call_args
        == [(m_user_config.return_value, ), {}])
    if start_year != 0:
        assert "config" in cves.__dict__


@pytest.mark.parametrize("config_path", [None, "", "PATH"])
def test_cves_config_path(patches, config_path):
    kwargs = (
        dict(config_path=config_path)
        if config_path is not None
        else {})
    cves = DummyDependencyCVEs("DEPENDENCIES", **kwargs)
    patched = patches(
        "pathlib",
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_plib, ):
        assert (
            cves.config_path
            == (m_plib.Path.return_value
                if config_path
                else None))

    if config_path:
        assert (
            m_plib.Path.call_args
            == [(config_path, ), {}])
    else:
        assert not m_plib.called
    assert "config_path" not in cves.__dict__


def test_cves_cpe_revmap(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "defaultdict",
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_dict, ):
        assert cves.cpe_revmap == m_dict.return_value

    assert (
        m_dict.call_args
        == [(set, ), {}])
    assert "cpe_revmap" in cves.__dict__


@pytest.mark.parametrize("data", [None, "", "CVES"])
async def test_cves_data(patches, data):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.cpe_revmap",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.cves",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.downloads",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")
    download = MagicMock()

    async def conc():
        for x in range(0, 5):
            download()
            yield

    with patched as (m_cpes, m_cves, m_downloads):
        m_cves.return_value = data
        m_downloads.side_effect = conc
        result = await cves.data

    assert (
        result
        == (data, m_cpes.return_value))
    assert len(download.call_args_list) == (0 if data else 5)
    assert (
        getattr(
            cves,
            check.ADependencyCVEs.data.cache_name)[
                "data"]
        == result)


async def test_cves_downloads(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "concurrent",
        "ADependencyCVEs.parse_cve_response",
        ("ADependencyCVEs.nist_downloads", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")
    download_mocks = []
    results = []

    async def conc(nist):
        for x in range(0, 5):
            download_mock = MagicMock()
            download_mocks.append(download_mock)
            yield download_mock

    with patched as (m_conc, m_parse, m_nist):
        m_conc.side_effect = conc

        async for download in cves.downloads:
            results.append(download)

    assert results == [d.url for d in download_mocks]
    assert (
        m_conc.call_args
        == [(m_nist.return_value,), {}])
    assert (
        m_parse.call_args_list
        == [[(dl, ), {}]
            for dl in download_mocks])

    assert not (
        getattr(
            cves,
            check.ADependencyCVEs.data.cache_name,
            None))


def test_cves_ignored_cves(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.config", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_config, ):
        assert cves.ignored_cves == m_config.return_value.get.return_value

    assert (
        m_config.return_value.get.call_args
        == [("ignored_cves", []), {}])
    assert "ignored_cves" not in cves.__dict__


def test_cves_nist_downloads(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.urls", dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.download", dict(new_callable=MagicMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_urls, m_download):
        m_urls.return_value = [f"URL{i}" for i in range(0, 5)]
        downloads = cves.nist_downloads
        assert isinstance(downloads, GeneratorType)
        assert (
            list(downloads)
            == [m_download.return_value for i in range(0, 5)])

    assert (
        m_download.call_args_list
        == [[(f'URL{i}',), {}] for i in range(0, 5)])

    assert "nist_downloads" not in cves.__dict__


def test_cves_scan_year_end(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "datetime",
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_dt, ):
        assert (
            cves.scan_year_end
            == m_dt.now.return_value.year.__add__.return_value)

    assert (
        m_dt.now.call_args
        == [(), {}])
    assert (
        m_dt.now.return_value.year.__add__.call_args
        == [(1, ), {}])
    assert "scan_year_end" not in cves.__dict__


def test_cves_scan_year_start(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.config",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_config, ):
        assert (
            cves.scan_year_start
            == m_config.return_value.__getitem__.return_value)

    assert (
        m_config.return_value.__getitem__.call_args
        == [("start_year", ), {}])

    assert "scan_year_start" not in cves.__dict__


def test_cves_scan_years(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "range",
        ("ADependencyCVEs.scan_year_end", dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.scan_year_start", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_range, m_end, m_start):
        assert cves.scan_years == m_range.return_value

    assert (
        m_range.call_args
        == [(m_start.return_value, m_end.return_value), {}])

    assert "scan_years" not in cves.__dict__


@pytest.mark.parametrize("session", [None, "SESSION"])
def test_cves_session(patches, session):
    cves = DummyDependencyCVEs("DEPENDENCIES", session=session)
    patched = patches(
        "aiohttp",
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_aiohttp, ):
        assert (
            cves.session
            == (session
                if session
                else m_aiohttp.ClientSession.return_value))

    assert "session" in cves.__dict__
    if session:
        assert not m_aiohttp.called
        return
    assert (
        m_aiohttp.ClientSession.call_args
        == [(), {}])


def test_cves_tracked_cpes(patches):
    mock_deps = [MagicMock() for m in range(0, 5)]
    mock_deps[3].cpe = None
    cves = DummyDependencyCVEs(mock_deps)
    assert (
        cves.tracked_cpes
        == {mock_deps[m].cpe: mock_deps[m]
            for m in range(0, 5) if m != 3})
    assert "tracked_cpes" in cves.__dict__


def test_cves_urls(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.config", dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.scan_years", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_config, m_years):
        m_years.return_value = [f"723{i}" for i in range(0, 5)]
        m_formatted_url = (
            m_config.return_value.__getitem__.return_value
            .format.return_value)
        assert (
            cves.urls
            == [m_formatted_url for u in range(0, 5)])

    assert (
        m_config.return_value.__getitem__.call_args_list
        == [[('nist_url',), {}]] * 5)
    assert "urls" not in cves.__dict__


@pytest.mark.parametrize("config_path", [None, "", "CONFIG_PATH"])
def test_cves_user_config(patches, config_path):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "utils",
        ("ADependencyCVEs.config_path", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_utils, m_config):
        m_config.return_value = config_path
        assert (
            cves.user_config
            == (m_utils.typed.return_value
                if config_path
                else {}))

    if not config_path:
        assert not m_utils.typed.called
        assert not m_utils.from_yaml.called
        return

    assert (
        m_utils.typed.call_args
        == [(dict, m_utils.from_yaml.return_value), {}])
    assert (
        m_utils.from_yaml.call_args
        == [(m_config.return_value, ), {}])
    assert "user_config" not in cves.__dict__


async def test_cves_download(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_session, ):
        aget = AsyncMock()
        m_session.return_value.get = aget
        assert await cves.download("URL") == aget.return_value

    assert (
        aget.call_args
        == [("URL", ), {}])


@pytest.mark.parametrize("len_cpes", [0, 1, 2])
@pytest.mark.parametrize("is_v3", [True, False])
@pytest.mark.parametrize("id_ignored", [True, False])
def test_cves_include_cve(patches, len_cpes, is_v3, id_ignored):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.ignored_cves",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    cve = MagicMock()
    cve.cpes.__len__.side_effect = lambda: len_cpes
    cve.is_v3 = is_v3

    with patched as (m_ignored, ):
        m_ignored.return_value.__contains__.return_value = id_ignored
        assert (
            cves.include_cve(cve)
            == (len_cpes > 0 and is_v3 and not id_ignored))


@pytest.mark.parametrize("cpe", [True, False])
@pytest.mark.parametrize(
    "cpe_cves",
    [[],
     [False, False, False],
     [True, False, True],
     [False, False, False],
     [True, True, True]])
async def test_cves_dependency_check(patches, cpe, cpe_cves):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "sorted",
        ("ADependencyCVEs.data",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.cpe_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")
    dep = MagicMock()
    dep.cpe = cpe
    _cpe_cves = {}
    results = []
    expected = []
    revmap = MagicMock()

    for i, cpe_cve in enumerate(cpe_cves):
        cve = MagicMock()
        cve.dependency_match.return_value = cpe_cve
        if cpe_cve and cpe:
            expected.append(cve)
        _cpe_cves[f"CVE{i}"] = cve

    with patched as (m_sorted, m_data, m_class):
        m_data.side_effect = AsyncMock(return_value=[_cpe_cves, revmap])
        m_sorted.return_value = _cpe_cves.keys()

        async for result in cves.dependency_check(dep):
            results.append(result)

    assert results == expected
    if not cpe:
        assert not m_data.called
        assert not m_class.called
        assert not m_sorted.called
        return
    assert (
        m_class.return_value.from_string.call_args
        == [(dep.cpe, ), {}])
    assert (
        m_sorted.call_args
        == [(revmap.get.return_value, ), {}])
    assert (
        revmap.get.call_args
        == [(m_class.return_value.from_string.return_value.vendor_normalized,
             []), {}])


@pytest.mark.parametrize("exclude_cves", [[], [1], [0, 1, 2]])
def test_cves_parse_cve_json(patches, exclude_cves):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.cve_class",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.cpe_revmap",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.cves",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.tracked_cpes",
         dict(new_callable=PropertyMock)),
        "ADependencyCVEs.include_cve",
        prefix="envoy.dependency.check.abstract.cves.cves")
    cve_json = MagicMock()
    cve_items = MagicMock()
    cve_items = [MagicMock(), MagicMock(), MagicMock()]
    cve_json.__getitem__.return_value = cve_items
    parsed_cves = [MagicMock(return_value=cve) for cve in cve_items]
    for cve in parsed_cves:
        cve.cpes = [MagicMock() for i in range(0, 5)]

    with patched as (m_class, m_cpes, m_cves, m_tracked, m_include):
        m_class.return_value.side_effect = (
            lambda cve_item, tracked: parsed_cves[cve_items.index(cve_item)])
        m_include.side_effect = (
            lambda cve: parsed_cves.index(cve) not in exclude_cves)
        assert not cves.parse_cve_json(cve_json)

    assert (
        m_class.return_value.call_args_list
        == [[(cve_item, m_tracked.return_value), {}]
            for cve_item in cve_items])
    assert (
        m_include.call_args_list
        == [[(cve, ), {}]
            for cve in parsed_cves])
    assert (
        m_cves.return_value.__setitem__.call_args_list
        == [[(cve.id, cve), {}]
            for i, cve in enumerate(parsed_cves) if i not in exclude_cves])
    expected = []
    for i, cve in enumerate(parsed_cves):
        if i in exclude_cves:
            continue
        for cpe in cve.cpes:
            expected.append((cpe, cve))
    assert (
        m_cpes.return_value.__getitem__.call_args_list
        == [[(cpe.vendor_normalized,), {}] for cpe, cve in expected])
    assert (
        m_cpes.return_value.__getitem__.return_value.add.call_args_list
        == [[(cve.id,), {}] for cpe, cve in expected])


@pytest.mark.parametrize(
    "raises",
    [None,
     aiohttp.client_exceptions.ClientPayloadError,
     gzip.BadGzipFile,
     Exception])
async def test_cves_parse_cve_response(patches, raises):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "gzip.decompress",
        "json",
        "ADependencyCVEs.parse_cve_json",
        prefix="envoy.dependency.check.abstract.cves.cves")
    download = AsyncMock()

    with patched as (m_gzip, m_json, m_parse):
        if raises == Exception:
            m_parse.side_effect = raises
            with pytest.raises(Exception):
                await cves.parse_cve_response(download)
        elif raises:
            exception = raises("AN ERROR")
            if raises == aiohttp.client_exceptions.ClientPayloadError:
                download.read.side_effect = exception
            else:
                m_gzip.side_effect = exception
            with pytest.raises(check.exceptions.CVECheckError) as e:
                await cves.parse_cve_response(download)
            assert (
                e.value.args[0]
                == f"Error downloading from {download.url}: AN ERROR")
        else:
            assert (
                await cves.parse_cve_response(download)
                is None)

    assert (
        download.read.call_args
        == [(), {}])
    if raises == aiohttp.client_exceptions.ClientPayloadError:
        assert not m_gzip.called
        assert not m_json.loads.called
        return
    assert (
        m_gzip.call_args
        == [(download.read.return_value, ), {}])
    if raises == gzip.BadGzipFile:
        assert not m_json.loads.called
        return
    assert (
        m_json.loads.call_args
        == [(m_gzip.return_value, ), {}])
    assert (
        m_parse.call_args
        == [(m_json.loads.return_value, ), {}])
