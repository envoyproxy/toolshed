
import gzip
from types import GeneratorType
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import aiohttp

import abstracts

from envoy.dependency.cve_scan import ACVEChecker, CVECheckError
from envoy.dependency.cve_scan.abstract.checker import NIST_URL_TPL


@abstracts.implementer(ACVEChecker)
class DummyCVEChecker:

    def __init__(self):
        pass

    @property
    def cpe_class(self):
        return super().cpe_class

    @property
    def cve_class(self):
        return super().cve_class

    @property
    def dependency_class(self):
        return super().dependency_class

    @property
    def dependency_metadata(self):
        return super().dependency_metadata

    @property
    def ignored_cves(self):
        return super().ignored_cves


def test_checker_constructor():

    with pytest.raises(TypeError):
        ACVEChecker()

    checker = DummyCVEChecker()
    assert checker.checks == ("cves", )

    iface_props = [
        "cpe_class", "cve_class",
        "dependency_class", "dependency_metadata"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(checker, prop)


@pytest.mark.parametrize("start_config", [0, 23])
@pytest.mark.parametrize(
    "start_raises", [None, NotImplementedError, Exception])
def test_checker_config(patches, start_config, start_raises):
    checker = DummyCVEChecker()
    patched = patches(
        "dict",
        "utils",
        ("ACVEChecker.config_path", dict(new_callable=PropertyMock)),
        ("ACVEChecker.nist_url_tpl", dict(new_callable=PropertyMock)),
        ("ACVEChecker.start_year", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_dict, m_utils, m_path, m_tpl, m_start):
        m_dict.return_value.__getitem__.return_value = start_config
        if start_raises:
            m_start.side_effect = start_raises
        if start_config == 0:
            if start_raises == NotImplementedError:
                with pytest.raises(CVECheckError) as e:
                    checker.config
                assert (
                    e.value.args[0]
                    == ("`start_year` must be specified in config "
                        f"({m_path.return_value}) or implemented "
                        "by `DummyCVEChecker`"))
            elif start_raises:
                with pytest.raises(start_raises):
                    checker.config
            else:
                assert checker.config == m_dict.return_value
        else:
            assert checker.config == m_dict.return_value

    assert (
        m_dict.call_args
        == [(), dict(nist_url=m_tpl.return_value, start_year=0)])
    assert (
        m_dict.return_value.update.call_args
        == [(m_utils.typed.return_value, ), {}])
    assert (
        m_utils.typed.call_args
        == [(m_dict, m_utils.from_yaml.return_value), {}])
    assert (
        m_utils.from_yaml.call_args
        == [(m_path.return_value, ), {}])
    assert (
        m_dict.return_value.__getitem__.call_args
        == [("start_year", ), {}])
    if start_config == 0 and not start_raises:
        assert (
            m_dict.return_value.__setitem__.call_args
            == [("start_year", m_start.return_value), {}])
    else:
        assert not m_dict.return_value.__setitem__.called
    if start_config != 0 or not start_raises:
        assert "config" in checker.__dict__


def test_checker_config_path(patches):
    checker = DummyCVEChecker()
    patched = patches(
        "pathlib",
        ("ACVEChecker.args", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_plib, m_args):
        assert checker.config_path == m_plib.Path.return_value

    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.config_path, ), {}])
    assert "config_path" not in checker.__dict__


async def test_checker_cve_data(patches):
    checker = DummyCVEChecker()
    patched = patches(
        "dict",
        "defaultdict",
        "concurrent",
        "ACVEChecker.parse_cve_response",
        ("ACVEChecker.log", dict(new_callable=PropertyMock)),
        ("ACVEChecker.nist_downloads", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    download_mocks = []

    async def conc(nist):
        for x in range(0, 5):
            download_mock = MagicMock()
            download_mocks.append(download_mock)
            yield download_mock

    with patched as (m_dict, m_ddict, m_conc, m_parse, m_log, m_nist):
        m_conc.side_effect = conc
        assert (
            await checker.cve_data
            == (m_dict.return_value, m_ddict.return_value))

    assert (
        m_log.return_value.info.call_args_list
        == [[(f"CVE data downloaded from: {dl.url}", ), {}]
            for dl in download_mocks])
    assert (
        m_conc.call_args
        == [(m_nist.return_value,), {}])
    assert (
        m_parse.call_args_list
        == [[(dl, m_dict.return_value, m_ddict.return_value), {}]
            for dl in download_mocks])
    assert "cve_data" not in checker.__dict__


def test_checker_dependencies(patches):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.dependency_class", dict(new_callable=PropertyMock)),
        ("ACVEChecker.dependency_metadata", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_dep_class, m_dep_metadata):
        m_dep_metadata.return_value = {f"k{i}": f"v{i}" for i in range(0, 5)}
        assert (
            checker.dependencies
            == [m_dep_class.return_value.return_value
                for i in range(0, 5)])

    assert (
        m_dep_class.return_value.call_args_list
        == [[(f"k{i}", f"v{i}"), {}] for i in range(0, 5)])
    assert "dependencies" in checker.__dict__


def test_checker_ignored_cves(patches):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.config", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_config, ):
        assert checker.ignored_cves == m_config.return_value.get.return_value

    assert (
        m_config.return_value.get.call_args
        == [("ignored_cves", []), {}])
    assert "ignored_cves" not in checker.__dict__


def test_checker_nist_downloads(patches):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.urls", dict(new_callable=PropertyMock)),
        ("ACVEChecker.download", dict(new_callable=MagicMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_urls, m_download):
        m_urls.return_value = [f"URL{i}" for i in range(0, 5)]
        downloads = checker.nist_downloads
        assert isinstance(downloads, GeneratorType)
        assert (
            list(downloads)
            == [m_download.return_value for i in range(0, 5)])

    assert (
        m_download.call_args_list
        == [[(f'URL{i}',), {}] for i in range(0, 5)])

    assert "nist_downloads" not in checker.__dict__


def test_checker_nist_url_tpl(patches):
    checker = DummyCVEChecker()
    assert checker.nist_url_tpl == NIST_URL_TPL
    assert "nist_url_tpl" not in checker.__dict__


def test_checker_provided_urls(patches):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.args", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_args, ):
        assert checker.provided_urls == m_args.return_value.urls

    assert "provided_urls" not in checker.__dict__


def test_checker_scan_year_end(patches):
    checker = DummyCVEChecker()
    patched = patches(
        "datetime",
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_dt, ):
        assert (
            checker.scan_year_end
            == m_dt.now.return_value.year.__add__.return_value)

    assert (
        m_dt.now.call_args
        == [(), {}])
    assert (
        m_dt.now.return_value.year.__add__.call_args
        == [(1, ), {}])
    assert "scan_year_end" not in checker.__dict__


def test_checker_scan_year_start(patches):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.config",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_config, ):
        assert (
            checker.scan_year_start
            == m_config.return_value.__getitem__.return_value)

    assert (
        m_config.return_value.__getitem__.call_args
        == [("start_year", ), {}])

    assert "scan_year_start" not in checker.__dict__


def test_checker_scan_years(patches):
    checker = DummyCVEChecker()
    patched = patches(
        "range",
        ("ACVEChecker.scan_year_end", dict(new_callable=PropertyMock)),
        ("ACVEChecker.scan_year_start", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_range, m_end, m_start):
        assert checker.scan_years == m_range.return_value

    assert (
        m_range.call_args
        == [(m_start.return_value, m_end.return_value), {}])

    assert "scan_years" not in checker.__dict__


def test_checker_session(patches):
    checker = DummyCVEChecker()
    patched = patches(
        "aiohttp",
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_aiohttp, ):
        assert checker.session == m_aiohttp.ClientSession.return_value

    assert (
        m_aiohttp.ClientSession.call_args
        == [(), {}])

    assert "session" in checker.__dict__


def test_checker_tracked_cpes(patches):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.dependencies", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_deps, ):
        mock_deps = [MagicMock() for m in range(0, 5)]
        mock_deps[3].cpe = None
        m_deps.return_value = mock_deps
        assert (
            checker.tracked_cpes
            == {mock_deps[m].cpe: mock_deps[m]
                for m in range(0, 5) if m != 3})
    assert "tracked_cpes" in checker.__dict__


@pytest.mark.parametrize("provided_urls", [None, [], ["URL"]])
def test_checker_urls(patches, provided_urls):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.config", dict(new_callable=PropertyMock)),
        ("ACVEChecker.provided_urls", dict(new_callable=PropertyMock)),
        ("ACVEChecker.scan_years", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_config, m_urls, m_years):
        m_urls.return_value = provided_urls
        m_years.return_value = [f"723{i}" for i in range(0, 5)]
        if provided_urls:
            assert checker.urls == provided_urls
        else:
            m_formatted_url = (
                m_config.return_value.__getitem__.return_value
                .format.return_value)
            assert (
                checker.urls
                == [m_formatted_url for u in range(0, 5)])

    if provided_urls:
        assert not m_config.called
        return

    assert (
        m_config.return_value.__getitem__.call_args_list
        == [[('nist_url',), {}]] * 5)


def test_checker_add_arguments(patches):
    checker = DummyCVEChecker()
    patched = patches(
        "checker.Checker.add_arguments",
        prefix="envoy.dependency.cve_scan.abstract.checker")
    parser = MagicMock()

    with patched as (m_super, ):
        assert not checker.add_arguments(parser)

    assert (
        m_super.call_args
        == [(parser, ), {}])
    assert (
        parser.add_argument.call_args_list
        == [[('config_path',), {}], [('urls',), {'nargs': '*'}]])


async def test_checker_check_cves(patches):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.cve_data",
         dict(new_callable=PropertyMock)),
        ("ACVEChecker.dependencies",
         dict(new_callable=PropertyMock)),
        ("ACVEChecker.log",
         dict(new_callable=PropertyMock)),
        "ACVEChecker.dependency_check",
        "ACVEChecker.error",
        "ACVEChecker.succeed",
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_data, m_deps, m_log, m_check, m_error, m_succeed):
        cve_data = (MagicMock(), MagicMock())
        m_data.side_effect = AsyncMock(return_value=cve_data)
        deps = [MagicMock() for i in range(0, 5)]
        m_deps.return_value = deps
        for i, dep in enumerate(deps):
            if i == 1:
                dep.cpe = None
            if i == 2:
                dep.errors = [5, 3, 1]
            elif i == 3:
                dep.errors = [4, 2]
            else:
                dep.errors = []
        m_check.side_effect = lambda dep, cves, cpe_revmap: dep.errors
        assert not await checker.check_cves()

    assert (
        m_log.return_value.info.call_args_list
        == [[(f"No CPE listed for: {deps[1].id}", ), {}]])
    assert (
        m_check.call_args_list
        == [[(dep, *cve_data), {}]
            for i, dep in enumerate(deps) if i != 1])
    formatted_failure = (
        f"{cve_data[0].__getitem__.return_value.format_failure.return_value}")
    assert (
        m_error.call_args_list
        == [[('cves',
              [formatted_failure
               for fail in dep.errors]), {}]
            for i, dep in enumerate(deps) if i in [2, 3]])
    assert (
        cve_data[0].__getitem__.call_args_list
        == [[(i, ), {}] for i in [1, 3, 5, 2, 4]])
    assert (
        m_succeed.call_args_list
        == [[('cves',
              [f"No CVEs found for: {dep.id}"]), {}]
            for i, dep in enumerate(deps) if i not in [1, 2, 3]])


@pytest.mark.parametrize("exclude_cves", [[], [1], [0, 1, 2]])
@pytest.mark.parametrize("cve_len", [0, 1, 2])
@pytest.mark.parametrize("match_cves", [[], [1], [0, 1, 2]])
def test_checker_dependency_match(patches, exclude_cves, cve_len, match_cves):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.cpe_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")
    dependency = MagicMock()
    cves = MagicMock()
    cpe_revmap = MagicMock()
    cpe_cves = [MagicMock() for i in range(0, cve_len)]
    cpe_revmap.get.return_value = cpe_cves

    class Matcher:
        count = 0

        def dep_match(self, dependency):
            if self.count in match_cves:
                self.count += 1
                return True
            self.count += 1
            return False

    matcher = Matcher()
    cves.__getitem__.return_value.dependency_match.side_effect = (
        matcher.dep_match)

    with patched as (m_class, ):
        recv_cves = checker.dependency_check(
            dependency, cves, cpe_revmap)
        assert isinstance(recv_cves, GeneratorType)
        assert (
            list(recv_cves)
            == [cve
                for i, cve
                in enumerate(cpe_cves)
                if i in match_cves])

    assert (
        m_class.return_value.from_string.call_args
        == [(dependency.cpe, ), {}])
    assert (
        cpe_revmap.get.call_args
        == [(m_class.return_value.from_string.return_value.vendor_normalized,
             []), {}])
    assert (
        cves.__getitem__.call_args_list
        == [[(cve, ), {}] for cve in cpe_cves])
    assert (
        cves.__getitem__.return_value.dependency_match.call_args_list
        == [[(dependency, ), {}] for cve in cpe_cves])


async def test_checker_download(patches):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_session, ):
        aget = AsyncMock()
        m_session.return_value.get = aget
        assert await checker.download("URL") == aget.return_value

    assert (
        aget.call_args
        == [("URL", ), {}])


@pytest.mark.parametrize("len_cpes", [0, 1, 2])
@pytest.mark.parametrize("is_v3", [True, False])
@pytest.mark.parametrize("id_ignored", [True, False])
def test_checker_include_cve(patches, len_cpes, is_v3, id_ignored):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.ignored_cves",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    cve = MagicMock()
    cve.cpes.__len__.side_effect = lambda: len_cpes
    cve.is_v3 = is_v3

    with patched as (m_ignored, ):
        m_ignored.return_value.__contains__.return_value = id_ignored
        assert (
            checker.include_cve(cve)
            == (len_cpes > 0 and is_v3 and not id_ignored))


async def test_checker_on_checks_complete(patches):
    checker = DummyCVEChecker()
    patched = patches(
        "checker.Checker.on_checks_complete",
        ("ACVEChecker.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    with patched as (m_super, m_session):
        m_session.return_value.close = AsyncMock()
        assert await checker.on_checks_complete() == m_super.return_value

    assert (
        m_session.return_value.close.call_args
        == [(), {}])


@pytest.mark.parametrize("exclude_cves", [[], [1], [0, 1, 2]])
def test_checker_parse_cve_json(patches, exclude_cves):
    checker = DummyCVEChecker()
    patched = patches(
        ("ACVEChecker.cve_class",
         dict(new_callable=PropertyMock)),
        ("ACVEChecker.tracked_cpes",
         dict(new_callable=PropertyMock)),
        "ACVEChecker.include_cve",
        prefix="envoy.dependency.cve_scan.abstract.checker")
    cve_json = MagicMock()
    cve_items = MagicMock()
    cpe_revmap = MagicMock()
    cve_items = [MagicMock(), MagicMock(), MagicMock()]
    cve_json.__getitem__.return_value = cve_items
    cves = [MagicMock(return_value=cve) for cve in cve_items]
    cve_dict = MagicMock()
    for cve in cves:
        cve.cpes = [MagicMock() for i in range(0, 5)]

    with patched as (m_class, m_tracked, m_include):
        m_class.return_value.side_effect = (
            lambda cve_item, tracked: cves[cve_items.index(cve_item)])
        m_include.side_effect = lambda cve: cves.index(cve) not in exclude_cves
        assert not checker.parse_cve_json(cve_json, cve_dict, cpe_revmap)

    assert (
        m_class.return_value.call_args_list
        == [[(cve_item, m_tracked.return_value), {}]
            for cve_item in cve_items])
    assert (
        m_include.call_args_list
        == [[(cve, ), {}]
            for cve in cves])
    assert (
        cve_dict.__setitem__.call_args_list
        == [[(cve.id, cve), {}]
            for i, cve in enumerate(cves) if i not in exclude_cves])
    expected = []
    for i, cve in enumerate(cves):
        if i in exclude_cves:
            continue
        for cpe in cve.cpes:
            expected.append((cpe, cve))
    assert (
        cpe_revmap.__getitem__.call_args_list
        == [[(cpe.vendor_normalized,), {}] for cpe, cve in expected])
    assert (
        cpe_revmap.__getitem__.return_value.add.call_args_list
        == [[(cve.id,), {}] for cpe, cve in expected])


@pytest.mark.parametrize(
    "raises",
    [None,
     aiohttp.client_exceptions.ClientPayloadError,
     gzip.BadGzipFile,
     Exception])
async def test_checker_parse_cve_response(patches, raises):
    checker = DummyCVEChecker()
    patched = patches(
        "gzip.decompress",
        "json",
        "ACVEChecker.parse_cve_json",
        prefix="envoy.dependency.cve_scan.abstract.checker")
    download = AsyncMock()
    cves = MagicMock()
    cpe_revmap = MagicMock()

    with patched as (m_gzip, m_json, m_parse):
        if raises == Exception:
            m_parse.side_effect = raises
            with pytest.raises(Exception):
                await checker.parse_cve_response(download, cves, cpe_revmap)
        elif raises:
            exception = raises("AN ERROR")
            if raises == aiohttp.client_exceptions.ClientPayloadError:
                download.read.side_effect = exception
            else:
                m_gzip.side_effect = exception
            with pytest.raises(CVECheckError) as e:
                await checker.parse_cve_response(download, cves, cpe_revmap)
            assert (
                e.value.args[0]
                == f"Error downloading from {download.url}: AN ERROR")
        else:
            assert (
                await checker.parse_cve_response(download, cves, cpe_revmap)
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
        == [(m_json.loads.return_value, cves, cpe_revmap), {}])
