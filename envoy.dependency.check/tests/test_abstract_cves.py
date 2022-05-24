
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.core import event

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

    @property
    def nist_downloader_class(self):
        return super().nist_downloader_class


@pytest.mark.parametrize("config_path", [None, "", "PATH"])
@pytest.mark.parametrize("loop", [None, "", "LOOP"])
@pytest.mark.parametrize("pool", [None, "", "POOL"])
@pytest.mark.parametrize("session", [None, "", "SESSION"])
def test_cves_constructor(patches, config_path, loop, pool, session):
    kwargs = {}
    if config_path is not None:
        kwargs["config_path"] = config_path
    if loop is not None:
        kwargs["loop"] = loop
    if pool is not None:
        kwargs["pool"] = pool
    if session is not None:
        kwargs["session"] = session

    with pytest.raises(TypeError):
        check.ADependencyCVEs("DEPENDENCIES", **kwargs)

    cves = DummyDependencyCVEs("DEPENDENCIES", **kwargs)
    assert cves.dependencies == "DEPENDENCIES"
    assert cves._config_path == config_path
    assert cves._loop == loop
    assert cves._pool == pool
    assert cves._session == session
    assert isinstance(cves, event.IReactive)

    with pytest.raises(NotImplementedError):
        cves.cpe_class
    with pytest.raises(NotImplementedError):
        cves.cve_class
    with pytest.raises(NotImplementedError):
        cves.nist_downloader_class

    assert cves.cves == {}
    assert "cves" in cves.__dict__


@pytest.mark.parametrize("config_path", [None, "", "CONFIG_PATH"])
def test_cves_config(patches, config_path):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "utils",
        ("ADependencyCVEs.config_path", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_utils, m_config):
        m_config.return_value = config_path
        assert (
            cves.config
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


def test_cves_cve_fields(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "qdict",
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_qdict, ):
        assert cves.cve_fields == m_qdict.return_value

    assert (
        m_qdict.call_args
        == [(),
            dict(
                score="impact/baseMetricV3/cvssV3/baseScore",
                severity="impact/baseMetricV3/cvssV3/baseSeverity",
                description="cve/description/description_data/0/value",
                last_modified_date="lastModifiedDate")])
    assert "cve_fields" not in cves.__dict__


@pytest.mark.parametrize("loaded", [True, False])
async def test_cves_data(patches, loaded):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("AwaitableGenerator",
         dict(new_callable=AsyncMock)),
        ("ADependencyCVEs.cpe_revmap",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.cves",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.downloads",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.loader",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_wait, m_cpes, m_cves, m_downloads, m_loader):
        m_loader.side_effect = AsyncMock(return_value=loaded)
        result = await cves.data

    assert (
        result
        == (m_cves.return_value, m_cpes.return_value))
    if loaded:
        assert not m_wait.called
        assert not m_downloads.called
    else:
        assert (
            m_wait.call_args
            == [(m_downloads.return_value, ), {}])
    assert (
        getattr(
            cves,
            check.ADependencyCVEs.data.cache_name)[
                "data"]
        == result)


@pytest.mark.parametrize("loaded", [True, False])
async def test_cves_downloads(iters, patches, loaded):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.cpe_class",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.cpe_revmap",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.cve_class",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.cves",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.nist_downloader",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.loader",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")
    results = []
    events = MagicMock()

    class DummyDownloader:
        cves = MagicMock()
        _cves = iters(dict, cb=lambda i: (f"ID{i}", f"CVE{i}")).items()
        cves.items.return_value = _cves
        cpe_revmap = MagicMock()
        urls = iters()

        async def __aiter__(self):
            events("DOWNLOADING")
            for url in self.urls:
                yield url

    class DummyLoader:

        def __await__(self):
            return self._wait().__await__()

        def __enter__(self):
            events("ENTERED")

        def __exit__(self, *exception):
            events("EXITED")

        async def _wait(self):
            events("AWAITED")
            return loaded

    downloader = DummyDownloader()
    loader = DummyLoader()

    with patched as patchy:
        (m_cpe_class, m_revmap,
         m_cve_class, m_cves, m_nist, m_loader) = patchy
        m_nist.return_value = downloader
        m_loader.return_value = loader
        async for download in cves.downloads:
            results.append(download)

    assert results == iters()
    assert not hasattr(
        cves,
        check.ADependencyCVEs.data.cache_name)
    if loaded:
        assert (
            events.call_args_list
            == [[("AWAITED", ), {}]])
        # assert not m_cves.__setitem__.called
        assert not downloader.cves.items.called
        assert not m_cve_class.called
        assert not m_cpe_class.called
        assert not m_revmap.called
        return
    assert (
        events.call_args_list
        == [[("AWAITED", ), {}],
            [("ENTERED", ), {}],
            [("DOWNLOADING", ), {}],
            [("EXITED", ), {}]])
    assert (
        m_cves.return_value.__setitem__.call_args_list
        == [[(id, m_cve_class.return_value.return_value, ), {}]
            for id, cve
            in downloader._cves])
    assert (
        m_revmap.return_value.update.call_args
        == [(downloader.cpe_revmap, ), {}])


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


def test_cves_loader(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "event",
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_event, ):
        assert cves.loader == m_event.Loader.return_value

    assert (
        m_event.Loader.call_args
        == [(), {}])
    assert "loader" in cves.__dict__


def test_cves_nist_downloader(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.cve_fields",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.ignored_cves",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.nist_downloader_class",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.pool",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.session",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.scan_year_start",
         dict(new_callable=PropertyMock)),
        ("ADependencyCVEs.tracked_cpes",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as patchy:
        (m_fields, m_ignored, m_class, m_pool,
         m_session, m_start, m_tracked) = patchy
        assert cves.nist_downloader == m_class.return_value.return_value

    assert (
        m_class.return_value.call_args
        == [(m_tracked.return_value, ),
            dict(
                cve_fields=m_fields.return_value,
                ignored_cves=m_ignored.return_value,
                since=m_start.return_value,
                pool=m_pool.return_value,
                session=m_session.return_value)])
    assert "nist_downloader" in cves.__dict__


def test_cves_scan_year_start(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("ADependencyCVEs.config",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_config, ):
        assert (
            cves.scan_year_start
            == m_config.return_value.get.return_value)

    assert (
        m_config.return_value.get.call_args
        == [("start_year", ), {}])

    assert "scan_year_start" not in cves.__dict__


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


def test_cves_tracked_cpes(iters, patches):
    mock_deps = iters(cb=lambda i: MagicMock())
    mock_deps[3].cpe = None
    cves = DummyDependencyCVEs(mock_deps)
    patched = patches(
        "ADependencyCVEs.cpe_filter_dict",
        prefix="envoy.dependency.check.abstract.cves.cves")

    with patched as (m_filter_dict, ):
        assert (
            cves.tracked_cpes
            == {mock_deps[m].cpe: m_filter_dict.return_value
                for m in range(0, 5) if m != 3})

    assert (
        m_filter_dict.call_args_list
        == [[(mock_deps[m], ), {}]
            for m in range(0, 5) if m != 3])
    assert "tracked_cpes" in cves.__dict__


def test_cves_cpe_filter_dict(patches):
    cves = DummyDependencyCVEs("DEPENDENCIES")
    patched = patches(
        "dict",
        prefix="envoy.dependency.check.abstract.cves.cves")
    dep = MagicMock()

    with patched as (m_dict, ):
        assert (
            cves.cpe_filter_dict(dep)
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            dict(
                version=dep.release_version,
                date=dep.release_date)])


@pytest.mark.parametrize("cpe", [True, False])
async def test_cves_dependency_check(patches, cpe):
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

    for i in range(0, 5):
        cve = MagicMock()
        if cpe:
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
