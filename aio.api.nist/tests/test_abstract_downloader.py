
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.api import nist


@abstracts.implementer(nist.ANISTDownloader)
class DummyNISTDownloader:

    @property
    def parser_class(self):
        return super().parser_class


@pytest.mark.parametrize("ignored_cves", [None, False, "IGNORED_CVES"])
@pytest.mark.parametrize("session", [None, False, "SESSION"])
@pytest.mark.parametrize("since", [None, False, "SINCE"])
@pytest.mark.parametrize("cve_fields", [None, False, "CVE_FIELDS"])
def test_downloader_constructor(ignored_cves, session, since, cve_fields):
    kwargs = {}
    if ignored_cves is not None:
        kwargs["ignored_cves"] = ignored_cves
    if session is not None:
        kwargs["session"] = session
    if since is not None:
        kwargs["since"] = since
    if cve_fields is not None:
        kwargs["cve_fields"] = cve_fields

    with pytest.raises(TypeError):
        nist.ANISTDownloader("TRACKED_CPES", **kwargs)
        return

    downloader = DummyNISTDownloader("TRACKED_CPES", **kwargs)
    assert downloader.tracked_cpes == "TRACKED_CPES"
    assert downloader.ignored_cves == ignored_cves
    assert downloader.cve_fields == cve_fields
    assert downloader._session == session
    assert downloader._since == since
    assert (
        downloader.nist_url_tpl
        == nist.abstract.downloader.NIST_URL_TPL)
    assert "nist_url_tpl" not in downloader.__dict__
    assert downloader.cves == {}
    assert "cves" in downloader.__dict__
    assert downloader.cpe_revmap == {}
    assert "cpe_revmap" in downloader.__dict__

    with pytest.raises(NotImplementedError):
        downloader.parser_class


async def test_downloader_dunder_aiter(patches):
    downloader = DummyNISTDownloader("TRACKED_CPES")
    patched = patches(
        ("ANISTDownloader.downloads",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.downloader")
    downloads = [MagicMock() for x in range(0, 5)]
    results = []

    async def iter_downloads():
        for dl in downloads:
            yield dl

    with patched as (m_downloads, ):
        m_downloads.side_effect = iter_downloads

        async for url in downloader:
            results.append(url)

    assert results == downloads


async def test_downloader_downloads(patches):
    downloader = DummyNISTDownloader("TRACKED_CPES")
    patched = patches(
        "concurrent",
        ("ANISTDownloader.downloaders",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.downloader")
    downloads = [MagicMock() for x in range(0, 5)]
    results = []

    async def iter_downloads(dls):
        for dl in downloads:
            yield dl

    with patched as (m_concurrent, m_downloaders):
        m_concurrent.side_effect = iter_downloads

        async for url in downloader.downloads:
            results.append(url)

    assert results == [dl.url for dl in downloads]
    assert (
        m_concurrent.call_args
        == [(m_downloaders.return_value, ), {}])


def test_downloader_downloaders(patches):
    downloader = DummyNISTDownloader("TRACKED_CPES")
    patched = patches(
        ("ANISTDownloader.download_and_parse",
         dict(new_callable=MagicMock())),
        ("ANISTDownloader.urls",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.downloader")
    urls = [MagicMock() for x in range(0, 5)]

    def iter_urls():
        for dl in urls:
            yield dl

    with patched as (m_parse, m_urls):
        m_urls.side_effect = iter_urls
        results = []
        for dl in downloader.downloaders:
            results.append(dl)

    assert results == [m_parse.return_value for url in urls]
    assert (
        m_parse.call_args_list
        == [[(url, ), {}] for url in urls])
    assert "downloaders" not in downloader.__dict__


@pytest.mark.parametrize("cve_fields", [None, "CVE_FIELDS"])
def test_downloader_parser(patches, cve_fields):
    kwargs = (
        dict(cve_fields=cve_fields)
        if cve_fields is not None
        else {})
    downloader = DummyNISTDownloader(
        "TRACKED_CPES",
        ignored_cves="IGNORED_CVES",
        **kwargs)
    patched = patches(
        ("ANISTDownloader.parser_class",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.downloader")

    with patched as (m_class, ):
        assert (
            downloader.parser
            == m_class.return_value.return_value)

    parser_kwargs = kwargs.copy()
    parser_kwargs["cve_fields"] = cve_fields
    assert (
        m_class.return_value.call_args
        == [("TRACKED_CPES", ),
            {**dict(ignored_cves="IGNORED_CVES"),
             **parser_kwargs}])
    assert "parser" in downloader.__dict__


def test_downloader_scan_year_end(patches):
    downloader = DummyNISTDownloader("TRACKED_CPES")
    patched = patches(
        "datetime",
        prefix="aio.api.nist.abstract.downloader")

    with patched as (m_dt, ):
        assert (
            downloader.scan_year_end
            == m_dt.now.return_value.year.__add__.return_value)

    assert (
        m_dt.now.call_args
        == [(), {}])
    assert (
        m_dt.now.return_value.year.__add__.call_args
        == [(1, ), {}])
    assert "scan_year_end" not in downloader.__dict__


@pytest.mark.parametrize("since", [None, "", 0, *range(2000, 2030)])
def test_downloader_since(patches, since):
    kwargs = (
        dict(since=since)
        if since
        else {})
    downloader = DummyNISTDownloader("TRACKED_CPES", **kwargs)
    patched = patches(
        "max",
        prefix="aio.api.nist.abstract.downloader")

    with patched as (m_max, ):
        assert (
            downloader.since
            == m_max.return_value)

    assert (
        m_max.call_args
        == [(since or nist.abstract.downloader.SCAN_FROM_YEAR,
             nist.abstract.downloader.SCAN_FROM_YEAR), {}])
    assert "since" not in downloader.__dict__


@pytest.mark.parametrize("session", [None, "SESSION"])
def test_downloader_session(patches, session):
    kwargs = (
        dict(session=session)
        if session is not None
        else {})
    downloader = DummyNISTDownloader("URLS", "TRACKED_CPES", **kwargs)
    patched = patches(
        "aiohttp",
        prefix="aio.api.nist.abstract.downloader")

    with patched as (m_http, ):
        assert (
            downloader.session
            == (session if session else m_http.ClientSession.return_value))

    if not session:
        assert (
            m_http.ClientSession.call_args
            == [(), {}])
    else:
        assert not m_http.ClientSession.called
    assert "session" in downloader.__dict__


def test_downloader_urls(patches):
    downloader = DummyNISTDownloader("DEPENDENCIES")
    patched = patches(
        ("ANISTDownloader.nist_url_tpl", dict(new_callable=PropertyMock)),
        ("ANISTDownloader.years", dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.downloader")

    with patched as (m_tpl, m_years):
        m_years.return_value = [f"Y{i}" for i in range(0, 5)]
        assert (
            downloader.urls
            == set([
                m_tpl.return_value.format.return_value
                for u in range(0, 5)]))
    assert "urls" not in downloader.__dict__


def test_downloader_years(patches):
    downloader = DummyNISTDownloader("TRACKED_CPES")
    patched = patches(
        "range",
        ("ANISTDownloader.scan_year_end", dict(new_callable=PropertyMock)),
        ("ANISTDownloader.since", dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.downloader")

    with patched as (m_range, m_end, m_start):
        assert downloader.years == m_range.return_value

    assert (
        m_range.call_args
        == [(m_start.return_value, m_end.return_value), {}])

    assert "scan_years" not in downloader.__dict__


def test_downloader_add(patches):
    downloader = DummyNISTDownloader("URLS", "TRACKED_CPES")
    patched = patches(
        ("ANISTDownloader.cves",
         dict(new_callable=PropertyMock)),
        ("ANISTDownloader.cpe_revmap",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.downloader")
    cves = MagicMock()
    cpe_revmap = MagicMock()

    with patched as (m_cves, m_revmap):
        assert not downloader.add(cves, cpe_revmap)

    assert (
        m_cves.return_value.update.call_args
        == [(cves, ), {}])
    assert (
        m_revmap.return_value.update.call_args
        == [(cpe_revmap, ), {}])


async def test_downloader_download_and_parse(patches):
    downloader = DummyNISTDownloader("URLS", "TRACKED_CPES")
    patched = patches(
        "logger",
        ("ANISTDownloader.session",
         dict(new_callable=PropertyMock)),
        "ANISTDownloader.add",
        "ANISTDownloader.parse",
        prefix="aio.api.nist.abstract.downloader")
    url = MagicMock()

    with patched as (m_logger, m_session, m_add, m_parse):
        m_parse.return_value = "FOO", "BAR"
        m_session.return_value.get = AsyncMock()
        assert (
            await downloader.download_and_parse(url)
            == m_session.return_value.get.return_value)

    assert (
        m_session.return_value.get.call_args
        == [(url, ), {}])
    assert (
        m_logger.debug.call_args_list
        == [[(f"Downloading CVE data: {url}", ), {}],
            [(f"CVE data saved: {url}", ), {}]])
    assert (
        m_add.call_args
        == [("FOO", "BAR"), {}])
    assert (
        m_parse.call_args
        == [(url,
             m_session.return_value.get.return_value.read.return_value, ),
            {}])
    assert (
        m_session.return_value.get.return_value.read.call_args
        == [(), {}])


async def test_downloader_parse(patches):
    downloader = DummyNISTDownloader("URLS", "TRACKED_CPES")
    patched = patches(
        "logger",
        ("ANISTDownloader.loop",
         dict(new_callable=PropertyMock)),
        ("ANISTDownloader.parser",
         dict(new_callable=PropertyMock)),
        ("ANISTDownloader.pool",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.downloader")
    data = MagicMock()

    with patched as (m_logger, m_loop, m_parser, m_pool):
        m_loop.return_value.run_in_executor = AsyncMock()
        assert (
            await downloader.parse("URL", data)
            == m_loop.return_value.run_in_executor.return_value)

    assert (
        m_logger.debug.call_args
        == [("Parsing CVE data: URL", ), {}])
    assert (
        m_loop.return_value.run_in_executor.call_args
        == [(m_pool.return_value,
             m_parser.return_value,
             data),
            {}])
