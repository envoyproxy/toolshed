
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.functional import async_property

from envoy.distribution.release import commands
from envoy.github.abstract.command import AGithubReleaseCommand


@pytest.mark.parametrize(
    "assets",
    [[], [dict(name=f"ASSET{i}") for i in range(0, 5)]])
async def test_release_command_assets(patches, assets):
    command = commands.AssetsCommand("CONTEXT")
    assert isinstance(command, AGithubReleaseCommand)
    patched = patches(
        ("AssetsCommand.release",
         dict(new_callable=PropertyMock)),
        ("AssetsCommand.runner",
         dict(new_callable=PropertyMock)),
        ("AssetsCommand.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_release, m_runner, m_version):
        m_release.return_value.assets = AsyncMock(return_value=assets)()
        assert (
            await command.run()
            == (None
                if assets
                else 1))

    if not assets:
        assert (
            list(m_runner.return_value.log.warning.call_args)
            == [(f"Version {m_version.return_value} has no assets", ), {}])
        assert not m_runner.return_value.stdout.called
        return
    assert (
        list(list(c) for c in m_runner.return_value.stdout.info.call_args_list)
        == [[(asset["name"],), {}] for asset in assets])


def test_release_command_create_add_arguments(patches):
    command = commands.CreateCommand("CONTEXT")
    parser = MagicMock()
    patched = patches(
        "AGithubReleaseCommand.add_arguments",
        prefix="envoy.distribution.release.commands")

    with patched as (m_super, ):
        assert not command.add_arguments(parser)

    assert (
        list(m_super.call_args)
        == [(parser, ), {}])
    assert (
        list(list(c) for c in parser.add_argument.call_args_list)
        == [[('--assets',),
             {'nargs': '*',
              'help': (
                  'Path to push assets from, can either be a directory '
                  'or a tarball')}]])


async def test_release_command_create_run(patches):
    command = commands.CreateCommand("CONTEXT")
    assert isinstance(command, AGithubReleaseCommand)
    patched = patches(
        "CreateCommand.format_response",
        ("CreateCommand.artefacts",
         dict(new_callable=PropertyMock)),
        ("CreateCommand.release",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_format, m_artefacts, m_release):
        mock_create = AsyncMock(return_value=dict(FOO="bar"))
        m_release.return_value.create = mock_create
        assert (
            await command.run()
            == m_format.return_value)

    assert (
        list(mock_create.call_args)
        == [(), dict(assets=m_artefacts.return_value)])
    assert (
        list(m_format.call_args)
        == [(), dict(FOO="bar")])


async def test_release_command_delete(patches):
    command = commands.DeleteCommand("CONTEXT")
    assert isinstance(command, AGithubReleaseCommand)
    patched = patches(
        ("DeleteCommand.release",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_release, ):
        mock_delete = AsyncMock()
        m_release.return_value.delete = mock_delete
        assert await command.run() == mock_delete.return_value

    assert (
        list(mock_delete.call_args)
        == [(), {}])


@pytest.mark.parametrize(
    "asset_types",
    [None,
     [],
     ([f"ASSET_TYPE{i}:FOO:BAR" for i in range(0, 5)]
      + [f"ASSET_TYPE{i}:FOO2:BAR2" for i in range(0, 5)])])
def test_release_command_fetch_asset_types(patches, asset_types):
    command = commands.FetchCommand("CONTEXT")
    patched = patches(
        "re",
        ("FetchCommand.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_re, m_args):
        m_args.return_value.asset_type = asset_types
        assert (
            command.asset_types
            == {asset_type.split(":")[0]: m_re.compile.return_value
                for asset_type in asset_types or []})

    assert (
        list(list(c) for c in m_re.compile.call_args_list)
        == [[(asset_type.split(":", 1)[1],), {}]
            for asset_type in asset_types or []])
    assert "asset_types" not in command.__dict__


def test_release_command_fetch_path(patches):
    command = commands.FetchCommand("CONTEXT")
    patched = patches(
        "pathlib",
        ("FetchCommand.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_plib, m_args):
        assert command.path == m_plib.Path.return_value

    assert (
        list(m_plib.Path.call_args)
        == [(m_args.return_value.path, ), {}])
    assert "path" not in command.__dict__


@pytest.mark.parametrize("find_latest", [True, False])
def test_release_command_fetch_find_latest(patches, find_latest):
    command = commands.FetchCommand("CONTEXT")
    patched = patches(
        ("FetchCommand.versions",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_versions, ):
        if find_latest:
            m_versions.return_value = ["0.2.3", "0.2", "0.3.4"]
        else:
            m_versions.return_value = ["0.2.3", "0.3.4"]
        assert command.find_latest == find_latest


@pytest.mark.parametrize("find_latest", [True, False])
async def test_release_command_fetch_releases(patches, find_latest):
    command = commands.FetchCommand("CONTEXT")
    patched = patches(
        ("FetchCommand.find_latest",
         dict(new_callable=PropertyMock)),
        ("FetchCommand.manager",
         dict(new_callable=PropertyMock)),
        ("FetchCommand.versions",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")
    mock_latest = AsyncMock()
    versions = [f"VERSION{i}" for i in range(0, 5)]

    class Wrapped:

        def __init__(self, name):
            self.name = name

        def __str__(self):
            return self.name

    mock_latest.return_value.__getitem__.side_effect = (
        lambda k: Wrapped(f"LATEST{k}"))

    with patched as (m_latest, m_manager, m_versions):
        m_latest.return_value = find_latest
        m_versions.return_value = versions
        m_manager.return_value.__getitem__.side_effect = lambda k: f"ITEM{k}"
        if find_latest:
            m_manager.return_value.latest = mock_latest()
            assert (
                await command.releases
                == {f'LATEST{version}': f'ITEMLATEST{version}'
                    for version in versions})
        else:
            assert (
                await command.releases
                == {version: f'ITEM{version}'
                    for version in versions})

    assert "releases" in getattr(command, async_property.cache_name)


def test_release_command_fetch_versions(patches):
    command = commands.FetchCommand("CONTEXT")
    patched = patches(
        ("FetchCommand.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_args, ):
        assert command.versions == m_args.return_value.version

    assert "versions" not in command.__dict__


def test_release_command_fetch_add_arguments(patches):
    command = commands.FetchCommand("CONTEXT")
    parser = MagicMock()
    patched = patches(
        "AGithubReleaseCommand.add_arguments",
        prefix="envoy.distribution.release.commands")

    with patched as (m_super, ):
        assert not command.add_arguments(parser)

    assert not m_super.called
    assert (
        list(list(c) for c in parser.add_argument.call_args_list)
        == [[('version',),
             {'nargs': '*',
              'help': (
                  'Version to retrieve assets for. '
                  'Can be specified multiple times')}],
            [('--path',),
             {'help': (
                 'Path to save assets to, can either be a directory '
                 'or a tarball path')}],
            [('--asset-type',),
             {'nargs': '*',
              'help': (
                  'Regex to match asset type and folder to fetch '
                  'assets into')}]])


@pytest.mark.parametrize(
    "releases",
    [[], ["RELEASE0"], [f"RELEASE{i}" for i in range(0, 5)]])
async def test_release_command_fetch_run(patches, releases):
    command = commands.FetchCommand("CONTEXT")
    assert isinstance(command, AGithubReleaseCommand)
    patched = patches(
        ("FetchCommand.asset_types",
         dict(new_callable=PropertyMock)),
        ("FetchCommand.path",
         dict(new_callable=PropertyMock)),
        ("FetchCommand.releases",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    releases = {r: AsyncMock() for r in releases}

    with patched as (m_types, m_path, m_releases):
        mock_releases = AsyncMock(return_value=releases)
        m_releases.side_effect = mock_releases
        assert not await command.run()

    for i, release in enumerate(releases.values()):
        assert (
            list(release.fetch.call_args)
            == [(m_path.return_value, m_types.return_value),
                {'append': i > 0}])


async def test_release_command_info(patches):
    command = commands.InfoCommand("CONTEXT")
    assert isinstance(command, AGithubReleaseCommand)
    patched = patches(
        "InfoCommand.format_response",
        ("InfoCommand.release",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_format, m_release):
        mock_release = AsyncMock()
        m_release.return_value.release = mock_release()
        assert (
            await command.run()
            == m_format.return_value)

    assert (
        list(m_format.call_args)
        == [(mock_release.return_value, ), {}])


@pytest.mark.parametrize(
    "releases",
    [[], [dict(tag_name=f"RELEASE{i}") for i in range(0, 5)]])
async def test_release_command_list(patches, releases):
    command = commands.ListCommand("CONTEXT")
    assert isinstance(command, AGithubReleaseCommand)
    patched = patches(
        ("ListCommand.runner",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_runner, ):
        mock_releases = AsyncMock(return_value=releases)
        m_runner.return_value.release_manager.releases = mock_releases()
        assert not await command.run()

    assert (
        list(list(c) for c in m_runner.return_value.stdout.info.call_args_list)
        == [[(release["tag_name"], ), {}]
            for release in releases])


def test_release_command_push_add_arguments(patches):
    command = commands.PushCommand("CONTEXT")
    parser = MagicMock()
    patched = patches(
        "AGithubReleaseCommand.add_arguments",
        prefix="envoy.distribution.release.commands")

    with patched as (m_super, ):
        assert not command.add_arguments(parser)

    assert (
        list(m_super.call_args)
        == [(parser, ), {}])
    assert (
        list(list(c) for c in parser.add_argument.call_args_list)
        == [[('--assets',),
             {'nargs': '*',
              'help': (
                  'Path to push assets from, can either be a directory '
                  'or a tarball')}]])


async def test_release_command_push_run(patches):
    command = commands.PushCommand("CONTEXT")
    assert isinstance(command, AGithubReleaseCommand)
    patched = patches(
        ("PushCommand.artefacts",
         dict(new_callable=PropertyMock)),
        ("PushCommand.release",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.commands")

    with patched as (m_artefacts, m_release):
        mock_push = AsyncMock()
        m_release.return_value.push = mock_push
        assert not await command.run()

    assert (
        list(mock_push.call_args)
        == [(m_artefacts.return_value, ), {}])
