
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.run.checker import Checker

from envoy.dependency.check import (
    ADependencyChecker, exceptions)


@abstracts.implementer(ADependencyChecker)
class DummyDependencyChecker:

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
    assert checker.checks == ("cves", )

    iface_props = ["dependency_class"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(checker, prop)


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
        ("ADependencyChecker.dependency_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_sorted, m_tuple, m_meta, m_class):
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
        == [[(i, dep), {}]
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
        == [[('--repository_locations',), {}],
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
