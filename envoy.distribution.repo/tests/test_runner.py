
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.distribution import repo


def test_runner_constructor():
    runner = repo.RepoBuildingRunner()
    assert isinstance(runner, repo.ARepoBuildingRunner)


def test_runner_archive(patches):
    runner = repo.RepoBuildingRunner()
    patched = patches(
        "pathlib",
        ("RepoBuildingRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.runner")

    with patched as (m_plib, m_args):
        assert runner.archive == m_plib.Path.return_value

    assert (
        list(m_plib.Path.call_args)
        == [(m_args.return_value.archive, ), {}])

    assert "archive" not in runner.__dict__


def test_runner_packages(patches):
    runner = repo.RepoBuildingRunner()
    patched = patches(
        "pathlib",
        ("RepoBuildingRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.runner")
    packages = [f"PACKAGE{i}" for i in range(0, 5)]

    with patched as (m_plib, m_args):
        m_args.return_value.packages = packages
        assert (
            runner.packages
            == tuple(m_plib.Path.return_value
                     for i in range(0, 5)))

    assert (
        list(m_plib.Path.call_args_list)
        == [[(package, ), {}] for package in packages])

    assert "packages" not in runner.__dict__


def test_runner_add_arguments(patches):
    runner = repo.RepoBuildingRunner()
    parser = MagicMock()
    patched = patches(
        "ARepoBuildingRunner.add_arguments",
        prefix="envoy.distribution.repo.runner")

    with patched as (m_super, ):
        assert not runner.add_arguments(parser)

    assert (
        list(m_super.call_args)
        == [(parser, ), {}])
    assert (
        list(list(c) for c in parser.add_argument.call_args_list)
        == [[('--packages',),
             {'nargs': '*'}],
            [('--archive',),
             {'nargs': '?'}]])


@pytest.mark.parametrize("archive", [True, False])
def test_runner_create_archive(patches, archive):
    runner = repo.RepoBuildingRunner()
    patched = patches(
        "tarfile",
        ("RepoBuildingRunner.archive",
         dict(new_callable=PropertyMock)),
        ("RepoBuildingRunner.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.runner")
    paths = [f"PATH{i}" for i in range(0, 5)]

    with patched as (m_tar, m_archive, m_log):
        if not archive:
            m_archive.return_value = None
        assert not runner.create_archive(*paths)

    if not archive:
        assert not m_tar.open.called
        assert (
            list(m_log.return_value.warning.call_args)
            == [("No `--archive` argument provided, dry run only", ), {}])
        return

    assert not m_log.called
    assert (
        list(m_tar.open.call_args)
        == [(m_archive.return_value, "w"), {}])
    tfile = m_tar.open.return_value.__enter__.return_value
    assert (
        list(list(c) for c in tfile.add.call_args_list)
        == [[(path, ), dict(arcname=".")]
            for path in paths])


def test_runner_extract_packages(patches):
    runner = repo.RepoBuildingRunner()
    patched = patches(
        "utils",
        ("RepoBuildingRunner.packages",
         dict(new_callable=PropertyMock)),
        ("RepoBuildingRunner.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.runner")

    with patched as (m_utils, m_packages, m_path):
        m_packages.return_value = [
            f"PACKAGES{i}" for i in range(0, 5)]
        assert not runner.extract_packages()

    assert (
        list(list(c) for c in m_utils.extract.call_args_list)
        == [[(m_path.return_value, p), {}]
            for p in m_packages.return_value])


@pytest.mark.asyncio
async def test_runner_run(patches):
    runner = repo.RepoBuildingRunner()
    patched = patches(
        "utils",
        "RepoBuildingRunner.create_archive",
        "RepoBuildingRunner.extract_packages",
        ("RepoBuildingRunner.published_repos",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.runner")
    create_args = [f"ARG{i}" for i in range(0, 3)]

    with patched as (m_utils, m_create, m_extract, m_repos):
        m_utils.async_list = AsyncMock(return_value=create_args)
        assert not await runner.run()

    assert (
        list(m_extract.call_args)
        == [(), {}])
    assert (
        list(m_create.call_args)
        == [tuple(create_args), {}])
    filter = m_utils.async_list.call_args.kwargs["filter"]
    assert (
        list(m_utils.async_list.call_args)
        == [(m_repos.return_value, ), dict(filter=filter)])
    assert filter("XYZ") == "XYZ"
    assert filter(None) is None
