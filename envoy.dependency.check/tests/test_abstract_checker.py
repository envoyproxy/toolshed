
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import gidgethub

import abstracts

from aio.core.functional import async_property
from aio.core.tasks import ConcurrentError
from aio.run.checker import Checker

from envoy.dependency.check import (
    ADependencyChecker, exceptions)


@abstracts.implementer(ADependencyChecker)
class DummyDependencyChecker:

    @property
    def access_token(self):
        return super().access_token

    @property
    def cves_class(self):
        return super().cves_class

    @property
    def dependency_class(self):
        return super().dependency_class

    @property
    def dependency_metadata(self):
        return super().dependency_metadata


def test_checker_constructor():

    with pytest.raises(TypeError):
        ADependencyChecker()

    checker = DummyDependencyChecker()
    assert isinstance(checker, Checker)
    assert checker.checks == ("cves", "dates")

    iface_props = [
        "dependency_class"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(checker, prop)


@pytest.mark.parametrize("arg", [True, False])
def test_checker_access_token(patches, arg):
    checker = DummyDependencyChecker()
    patched = patches(
        "os",
        "pathlib",
        ("ADependencyChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_os, m_plib, m_args):
        if not arg:
            m_args.return_value.github_token = None
        assert (
            checker.access_token
            == ((m_plib.Path.return_value
                       .read_text.return_value
                       .strip.return_value)
                if arg
                else m_os.getenv.return_value))

    if arg:
        assert not m_os.getenv.called
        assert (
            m_plib.Path.call_args
            == [(m_args.return_value.github_token, ), {}])
        assert (
            m_plib.Path.return_value.read_text.call_args
            == [(), {}])
        assert (
            m_plib.Path.return_value
                       .read_text.return_value
                       .strip.call_args
            == [(), {}])
    else:
        assert not m_plib.Path.called
        assert (
            m_os.getenv.call_args
            == [("GITHUB_TOKEN", ), {}])
    assert "access_token" not in checker.__dict__


def test_checker_cve_config(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_args, ):
        assert checker.cve_config == m_args.return_value.cve_config

    assert "cve_config" not in checker.__dict__


def test_checker_cves(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.dependencies",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.cve_config",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.cves_class",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_deps, m_config, m_class, m_session):
        assert checker.cves == m_class.return_value.return_value

    assert (
        m_class.return_value.call_args
        == [(m_deps.return_value, ),
            dict(config_path=m_config.return_value,
                 session=m_session.return_value)])
    assert "cves" in checker.__dict__


@pytest.mark.parametrize(
    "deps",
    [[],
     [(i, MagicMock()) for i in range(0, 5)]])
def test_checker_dependencies(patches, deps):
    checker = DummyDependencyChecker()
    patched = patches(
        "sorted",
        "tuple",
        ("ADependencyChecker.dependency_metadata",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.github",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.dependency_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_sorted, m_tuple, m_meta, m_github, m_class):
        m_meta.return_value.items.return_value = deps
        assert checker.dependencies == m_tuple.return_value

    assert (
        m_tuple.call_args
        == [(m_sorted.return_value, ), {}])
    assert (
        m_sorted.call_args
        == [([m_class.return_value.return_value] * len(deps), ), {}])
    assert (
        m_class.return_value.call_args_list
        == [[(i, dep, m_github.return_value), {}]
            for i, dep in deps])
    assert "dependencies" in checker.__dict__


def test_checker_dependency_metadata(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "json",
        ("ADependencyChecker.repository_locations_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_json, m_path):
        assert (
            checker.dependency_metadata
            == m_json.loads.return_value)

    assert (
        m_json.loads.call_args
        == [(m_path.return_value.read_text.return_value, ), {}])
    assert (
        m_path.return_value.read_text.call_args
        == [(), {}])
    assert "dependency_metadata" not in checker.__dict__


@pytest.mark.parametrize("token", [True, False])
def test_checker_disabled_checks(patches, token):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.access_token",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")
    expected = (
        dict(dates="No Github access token supplied")
        if not token
        else {})

    with patched as (m_token, ):
        m_token.return_value = token
        assert checker.disabled_checks == expected

    assert "disabled_checks" in checker.__dict__


def test_checker_github(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "github",
        ("ADependencyChecker.access_token",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_github, m_token, m_session):
        assert checker.github == m_github.GithubAPI.return_value

    assert (
        m_github.GithubAPI.call_args
        == [(m_session.return_value, ""),
            dict(oauth_token=m_token.return_value)])
    assert "github" in checker.__dict__


@pytest.mark.parametrize(
    "github_urls",
    [[],
     [False, False, True],
     [True, False, True],
     [False, False, False],
     [True, True, True]])
@pytest.mark.parametrize(
    "github_versions",
    [[False, False, True],
     [True, False, True],
     [False, False, False],
     [True, True, True]])
@pytest.mark.parametrize("raises", [BaseException, exceptions.BadGithubURL])
def test_checker_github_dependencies(
        patches, github_urls, github_versions, raises):
    checker = DummyDependencyChecker()
    patched = patches(
        "tuple",
        ("ADependencyChecker.dependencies",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")
    dependencies = []
    expected = []
    not_github = []
    errors = []
    urls = [f"URL{i}" for i in range(0, 3)]
    error = raises("AN ERROR OCCURRED")
    for i, github_url in enumerate(github_urls):
        github_version = github_versions[i]
        dep = MagicMock()
        dep.github_url = github_url
        dep.urls = urls
        github_version_prop = PropertyMock()
        type(dep).github_version = github_version_prop
        if not github_version:
            github_version_prop.side_effect = error
        if github_url:
            if not github_version:
                errors.append(dep)
            else:
                expected.append(dep)
        else:
            not_github.append(dep)
        dependencies.append(dep)

    joined_urls = "\n".join(urls)

    with patched as (m_tuple, m_deps, m_log):
        m_deps.return_value = dependencies
        if errors and raises == BaseException:
            with pytest.raises(BaseException) as e:
                checker.github_dependencies
            assert e.value == error
        else:
            assert checker.github_dependencies == m_tuple.return_value

    if errors and raises == BaseException:
        assert not m_tuple.called
        return
    assert (
        m_tuple.call_args
        == [(expected, ), {}])
    if expected == dependencies:
        assert not m_log.called
    assert (
        m_log.return_value.info.call_args_list
        == [[(f"{dep.id} is not a GitHub repository\n{joined_urls}", ), {}]
            for dep in not_github])
    assert "github_dependencies" in checker.__dict__


def test_checker_repository_locations_path(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "pathlib",
        ("ADependencyChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_plib, m_args):
        assert (
            checker.repository_locations_path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.repository_locations, ), {}])
    assert "repository_locations_path" not in checker.__dict__


def test_checker_session(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "aiohttp",
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_aiohttp, ):
        assert checker.session == m_aiohttp.ClientSession.return_value

    assert (
        m_aiohttp.ClientSession.call_args
        == [(), {}])
    assert "session" in checker.__dict__


def test_checker_fix(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_args, ):
        assert checker.fix == m_args.return_value.fix

    assert "fix" not in checker.__dict__


def test_checker_add_arguments(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "checker.Checker.add_arguments",
        prefix="envoy.dependency.check.abstract.checker")
    parser = MagicMock()

    with patched as (m_super, ):
        assert not checker.add_arguments(parser)

    assert (
        m_super.call_args
        == [(parser, ), {}])
    assert (
        parser.add_argument.call_args_list
        == [[('--github_token',), {}],
            [('--repository_locations',), {}],
            [('--cve_config',), {}]])


async def test_checker_check_cves(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.dependencies",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.dep_cve_check",
        prefix="envoy.dependency.check.abstract.checker")
    deps = [MagicMock() for i in range(0, 5)]

    with patched as (m_deps, m_check):
        m_deps.return_value = deps
        assert not await checker.check_cves()

    assert (
        m_check.call_args_list
        == [[(mock,), {}] for mock in deps])


async def test_checker_check_dates(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.github_dependencies",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.dep_date_check",
        prefix="envoy.dependency.check.abstract.checker")
    deps = [MagicMock() for i in range(0, 5)]

    with patched as (m_deps, m_check):
        m_deps.return_value = deps
        assert not await checker.check_dates()

    assert (
        m_check.call_args_list
        == [[(mock,), {}] for mock in deps])


@pytest.mark.parametrize("cpe", [True, False])
@pytest.mark.parametrize("failed", [0, 1, 3])
async def test_checker_dep_cve_check(patches, cpe, failed):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.cves",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.log",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.succeed",
        "ADependencyChecker.warn",
        prefix="envoy.dependency.check.abstract.checker")
    dep = MagicMock()
    dep.cpe = cpe
    failures = [MagicMock() for x in range(0, failed)]

    async def iter_failure(dep):
        for fail in failures:
            yield fail

    with patched as (m_cves, m_log, m_succeed, m_warn):
        m_cves.return_value.dependency_check.side_effect = iter_failure
        assert not await checker.dep_cve_check(dep)

    if not cpe:
        assert not m_cves.called
        assert not m_warn.called
        assert not m_succeed.called
        assert (
            m_log.return_value.info.call_args
            == [(f"No CPE listed for: {dep.id}", ), {}])
        return
    assert not m_log.called
    if not failures:
        assert not m_warn.called
        assert (
            m_succeed.call_args
            == [("cves",
                 [f"No CVEs found for: {dep.id}"]),
                {}])
        return
    assert (
        m_warn.call_args
        == [("cves",
             [f"{cve.format_failure.return_value}"
              for cve in failures]),
            {}])
    for failure in failures:
        assert (
            failure.format_failure.call_args
            == [(dep, ), {}])


@pytest.mark.parametrize("gh_date", [None, "GH_DATE"])
@pytest.mark.parametrize("mismatch", [True, False])
async def test_checker_dep_date_check(patches, gh_date, mismatch):
    checker = DummyDependencyChecker()
    patched = patches(
        "ADependencyChecker.error",
        "ADependencyChecker.succeed",
        prefix="envoy.dependency.check.abstract.checker")

    class DummyDepRelease:

        @async_property
        async def date(self):
            return gh_date

    class DummyDep:
        id = "DUMMY_DEP"
        release_date = "DUMMY_RELEASE_DATE"

        @property
        def release(self):
            return DummyDepRelease()

        @async_property
        async def release_date_mismatch(self):
            return mismatch

    dep = DummyDep()

    with patched as (m_error, m_succeed):
        assert not await checker.dep_date_check(dep)

    if not gh_date:
        assert (
            m_error.call_args
            == [("dates",
                 ["DUMMY_DEP is a GitHub repository with no no inferrable "
                  "release date"]),
                {}])
        assert not m_succeed.called
        return
    if mismatch:
        assert (
            m_error.call_args
            == [("dates",
                 ["Date mismatch: DUMMY_DEP "
                  f"DUMMY_RELEASE_DATE != {gh_date}"]),
                {}])
        assert not m_succeed.called
        return
    assert not m_error.called
    assert (
        m_succeed.call_args
        == [("dates", ["Date matches (DUMMY_RELEASE_DATE): DUMMY_DEP"]),
            {}])


async def test_checker_on_checks_complete(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "checker.Checker.on_checks_complete",
        ("ADependencyChecker.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_super, m_session):
        m_session.return_value.close = AsyncMock()
        assert await checker.on_checks_complete() == m_super.return_value

    assert (
        m_session.return_value.close.call_args
        == [(), {}])


@pytest.mark.parametrize(
    "downloads",
    [[],
     [f"D{i}" for i in range(0, 5)]])
async def test_checker_preload_cves(patches, downloads):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.cves",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    async def iter_downloads():
        for download in downloads:
            yield download

    with patched as (m_cves, m_log):
        m_cves.return_value.downloads = iter_downloads()
        assert not await checker.preload_cves()

    if downloads:
        assert (
            m_log.return_value.debug.call_args_list
            == [[(f"Preloaded cve data: {download}", ), {}]
                for download in downloads])
    else:
        assert not m_log.called

    assert (
        ADependencyChecker.preload_cves.when
        == ('cves',))
    assert (
        ADependencyChecker.preload_cves.blocks
        == ('cves',))
    assert (
        ADependencyChecker.preload_cves.unless
        == ())
    assert (
        ADependencyChecker.preload_cves.catches
        == (exceptions.CVECheckError,))


@pytest.mark.parametrize(
    "deps",
    [[],
     [f"DEP{i}" for i in range(0, 5)]])
async def test_checker_preload_dates(patches, deps):
    checker = DummyDependencyChecker()
    patched = patches(
        "inflate",
        ("ADependencyChecker.log",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.github_dependencies",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    async def iter_deps(iterable, cb):
        for dep in deps:
            mock_dep = MagicMock()
            mock_dep.id = dep
            yield mock_dep

    with patched as (m_inflate, m_log, m_gh_deps):
        m_inflate.side_effect = iter_deps
        assert not await checker.preload_dates()

    cb = m_inflate.call_args[0][1]
    item = MagicMock()
    assert cb(item) == (item.release.date, )
    assert (
        m_inflate.call_args
        == [(m_gh_deps.return_value, cb), {}])
    if deps:
        assert (
            m_log.return_value.debug.call_args_list
            == [[(f"Preloaded release date: {dep}", ), {}]
                for dep in deps])
    else:
        assert not m_log.called
    assert (
        ADependencyChecker.preload_dates.when
        == ('dates',))
    assert (
        ADependencyChecker.preload_dates.blocks
        == ('dates',))
    assert (
        ADependencyChecker.preload_dates.catches
        == (ConcurrentError, gidgethub.GitHubException))
