
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.functional import async_property

from envoy.distribution import repo


@abstracts.implementer(repo.AAptly)
class DummyAptly:

    @property
    def aptly_command(self):
        return super().aptly_command

    @property
    def log(self):
        return super().log


def test_aaptly_constructor():
    assert DummyAptly()


@pytest.mark.parametrize("iface_prop", ["aptly_command", "log"])
def test_aaptly_iface_props(iface_prop):
    with pytest.raises(NotImplementedError):
        getattr(DummyAptly(), iface_prop)


@pytest.mark.asyncio
async def test_aaptly_aptly_config(patches):
    aptly = DummyAptly()
    patched = patches(
        "json",
        ("AAptly.aptly",
         dict(new_callable=AsyncMock)),
        prefix="envoy.distribution.repo.deb")

    with patched as (m_json, m_aptly):
        assert (
            await aptly.aptly_config
            == m_json.loads.return_value)

    assert (
        list(m_aptly.call_args)
        == [("config", "show"), {}])
    assert (
        list(m_json.loads.call_args)
        == [(m_aptly.return_value, ), {}])
    assert async_property.is_cached(aptly, "aptly_config")


@pytest.mark.asyncio
async def test_aaptly_aptly_published(patches):
    aptly = DummyAptly()
    patched = patches(
        "AAptly.aptly",
        prefix="envoy.distribution.repo.deb")
    parts = [MagicMock() for i in range(0, 3)]

    with patched as (m_aptly, ):
        mock_strip = MagicMock()
        m_aptly.return_value.strip = mock_strip
        mock_split = mock_strip.return_value.split
        mock_split.return_value = parts
        assert (
            await aptly.aptly_published
            == [p.split.return_value.__getitem__.return_value
                for p in parts])

    assert (
        list(m_aptly.call_args)
        == [("publish", "list", "-raw"), {}])
    assert (
        list(mock_strip.call_args)
        == [(), {}])
    assert (
        list(mock_split.call_args)
        == [("\n", ), {}])
    for part in parts:
        assert (
            list(part.split.call_args)
            == [(" ", ), {}])
        assert (
            list(part.split.return_value.__getitem__.call_args)
            == [(1, ), {}])
    assert not async_property.is_cached(aptly, "published")


@pytest.mark.asyncio
async def test_aaptly_aptly_root_dir(patches):
    aptly = DummyAptly()
    patched = patches(
        "pathlib",
        ("AAptly.aptly_config",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")

    with patched as (m_plib, m_config):
        mock_config = AsyncMock()
        m_config.side_effect = mock_config
        assert (
            await aptly.aptly_root_dir
            == m_plib.Path.return_value)

    assert (
        list(mock_config.return_value.__getitem__.call_args)
        == [("rootDir", ), {}])
    assert (
        list(m_plib.Path.call_args)
        == [(mock_config.return_value.__getitem__.return_value, ), {}])
    assert not async_property.is_cached(aptly, "aptly_root_dir")


@pytest.mark.asyncio
async def test_aaptly_aptly_repos(patches):
    aptly = DummyAptly()
    patched = patches(
        "AAptly.aptly",
        prefix="envoy.distribution.repo.deb")

    with patched as (m_aptly, ):
        mock_strip = MagicMock()
        m_aptly.return_value.strip = mock_strip
        assert (
            await aptly.aptly_repos
            == mock_strip.return_value.split.return_value)

    assert (
        list(m_aptly.call_args)
        == [("repo", "list", "-raw"), {}])
    assert (
        list(mock_strip.call_args)
        == [(), {}])
    assert (
        list(mock_strip.return_value.split.call_args)
        == [("\n", ), {}])
    assert not async_property.is_cached(aptly, "repos")


@pytest.mark.asyncio
async def test_aaptly_aptly_snapshots(patches):
    aptly = DummyAptly()
    patched = patches(
        "AAptly.aptly",
        prefix="envoy.distribution.repo.deb")

    with patched as (m_aptly, ):
        mock_strip = MagicMock()
        m_aptly.return_value.strip = mock_strip
        assert (
            await aptly.aptly_snapshots
            == mock_strip.return_value.split.return_value)

    assert (
        list(m_aptly.call_args)
        == [("snapshot", "list", "-raw"), {}])
    assert (
        list(mock_strip.call_args)
        == [(), {}])
    assert (
        list(mock_strip.return_value.split.call_args)
        == [("\n", ), {}])
    assert not async_property.is_cached(aptly, "snapshots")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "return_code",
    [None] + list(range(0, 3)))
@pytest.mark.parametrize("stderr", [True, False])
@pytest.mark.parametrize("args", [(), tuple(f"ARG{i}" for i in range(0, 3))])
async def test_aaptly_aptly_aptly(patches, return_code, stderr, args):
    aptly = DummyAptly()
    patched = patches(
        "aio",
        ("AAptly.aptly_command",
         dict(new_callable=PropertyMock)),
        ("AAptly.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")

    with patched as (m_aio, m_command, m_log):
        mock_run = AsyncMock()
        mock_run.return_value.returncode = return_code
        mock_run.return_value.stderr = MagicMock()
        if not stderr:
            mock_run.return_value.stderr.strip.return_value = None
        m_aio.subprocess.run = mock_run
        command = (m_command.return_value, )
        if args:
            command += args
        if return_code:
            with pytest.raises(repo.AptlyError) as e:
                await aptly.aptly(*args)
        else:
            assert (
                await aptly.aptly(*args)
                == mock_run.return_value.stdout)

    assert (
        list(m_aio.subprocess.run.call_args)
        == [(command, ),
            dict(capture_output=True, encoding="utf-8")])
    if return_code:
        assert (
            e.value.args[0]
            == ("Error running aptly "
                f"({command}):\n{mock_run.return_value.stderr}"))
        assert not mock_run.return_value.stderr.strip.called
        assert not m_log.called
        return
    assert (
        list(mock_run.return_value.stderr.strip.call_args)
        == [(), {}])
    if not stderr:
        assert not m_log.called
        return
    assert (
        list(m_log.return_value.info.call_args)
        == [(mock_run.return_value.stderr, ), {}])


# note: this is a classmethod on RepoManagers
def test_deb_repomanager_add_arguments():
    parser = MagicMock()
    assert not repo.DebRepoManager.add_arguments(parser)
    assert (
        list(list(c) for c in parser.add_argument.call_args_list)
        == [[('--deb_aptly_command',), {'nargs': '?'}]])


@pytest.mark.parametrize("aptly_command", [None, "APTLY"])
def test_deb_repomanager_constructor(patches, aptly_command):
    patched = patches(
        "ARepoManager.__init__",
        prefix="envoy.distribution.repo.deb")
    kwargs = (
        dict(aptly_command=aptly_command)
        if aptly_command
        else {})

    with patched as (m_super, ):
        m_super.return_value = None
        manager = repo.DebRepoManager(
            "NAME", "PATH", "CONFIG", "LOG", "STDOUT", **kwargs)

    assert manager._aptly_command == aptly_command
    assert manager.file_types == r".*(\.deb|\.changes)$"
    assert (
        list(m_super.call_args)
        == [(manager, "NAME", "PATH", "CONFIG", "LOG", "STDOUT"), {}])


@pytest.mark.parametrize("cmd", [None, "TESTAPTLY"])
@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("which", [None, "TESTENVAPTLY"])
def test_deb_repomanager_aptly_command(patches, cmd, exists, which):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "pathlib",
        "shutil",
        prefix="envoy.distribution.repo.deb")
    no_command = not which and not cmd
    if cmd:
        manager._aptly_command = cmd

    with patched as (m_plib, m_shutil):
        m_shutil.which.return_value = which
        m_plib.Path.return_value.exists.return_value = exists
        if no_command or not exists:
            with pytest.raises(repo.DebRepoError) as e:
                manager.aptly_command
        else:
            assert manager.aptly_command == m_plib.Path.return_value

    if no_command:
        assert (
            e.value.args[0]
            == "Unable to find aptly command, and none provided")
        assert not m_plib.Path.called
        return

    assert (
        list(m_plib.Path.call_args)
        == [(cmd or which, ), {}])

    if exists:
        assert "aptly_command" in manager.__dict__
    else:
        assert (
            e.value.args[0]
            == f"Unable to find aptly command: {m_plib.Path.return_value}")


def test_deb_repomanager_changes_files():
    path = MagicMock()
    name = MagicMock()
    manager = repo.DebRepoManager(
        name, path, "CONFIG", "LOG", "STDOUT")
    paths = [f"PATH{i}" for i in range(0, 5)]
    path.glob.return_value = paths
    assert manager.changes_files == tuple(paths)
    assert (
        list(path.glob.call_args)
        == [(f"**/{name}/*.changes", ), {}])
    assert "changes_files" in manager.__dict__


def test_deb_repomanager_distros(patches):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "set",
        "chain",
        ("DebRepoManager.versions",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")

    with patched as (m_set, m_chain, m_versions):
        assert manager.distros == m_set.return_value

    assert (
        list(m_set.call_args)
        == [(m_chain.from_iterable.return_value, ), {}])
    assert (
        list(m_chain.from_iterable.call_args)
        == [(m_versions.return_value.values.return_value, ), {}])
    assert (
        list(m_versions.return_value.values.call_args)
        == [(), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("exists", [True, False])
async def test_deb_repomanager_create_distro(patches, exists):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.drop_distro",
        "DebRepoManager.distro_exists",
        "DebRepoManager.aptly",
        ("DebRepoManager.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")

    with patched as (m_rm, m_exists, m_aptly, m_log):
        m_exists.return_value = exists
        mock_strip = MagicMock()
        m_aptly.return_value.strip = mock_strip
        assert not await manager.create_distro("DISTRO")

    assert (
        list(m_exists.call_args)
        == [("DISTRO", ), {}])
    if exists:
        assert (
            list(m_rm.call_args)
            == [("DISTRO", ), {}])
    else:
        assert not m_rm.called
    assert (
        list(m_log.return_value.notice.call_args)
        == [("Creating deb distribution: DISTRO", ), {}])
    assert (
        list(m_aptly.call_args)
        == [("repo", "create",
             "-distribution=\"DISTRO\"",
             "-component=main",
             "DISTRO"), {}])
    mock_split = mock_strip.return_value.split
    assert (
        list(m_log.return_value.success.call_args)
        == [(mock_split.return_value.__getitem__.return_value, ), {}])
    assert (
        list(mock_strip.call_args)
        == [(), {}])
    assert (
        list(mock_split.call_args)
        == [("\n", ), {}])
    assert (
        list(mock_split.return_value.__getitem__.call_args)
        == [(0, ), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("exists", [True, False])
async def test_deb_repomanager_create_snapshot(patches, exists):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.drop_snapshot",
        "DebRepoManager.snapshot_exists",
        "DebRepoManager.aptly",
        ("DebRepoManager.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")

    with patched as (m_rm, m_exists, m_aptly, m_log):
        m_exists.return_value = exists
        mock_strip = MagicMock()
        m_aptly.return_value.strip = mock_strip
        assert not await manager.create_snapshot("DISTRO")

    assert (
        list(m_exists.call_args)
        == [("DISTRO", ), {}])
    if exists:
        assert (
            list(m_rm.call_args)
            == [("DISTRO", ), {}])
    else:
        assert not m_rm.called
    assert (
        list(m_aptly.call_args)
        == [("snapshot", "create",
             "DISTRO", "from", "repo", "DISTRO"), {}])
    assert (
        list(m_log.return_value.success.call_args)
        == [(mock_strip.return_value, ), {}])
    assert (
        list(mock_strip.call_args)
        == [(), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_name", [f"REPO{i}" for i in range(0, 5)])
async def test_deb_repomanager_distro_exists(patches, repo_name):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        ("DebRepoManager.aptly_repos",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")
    repos = [f"REPO{i}" for i in range(1, 3)]

    with patched as (m_repos, ):
        m_repos.side_effect = AsyncMock(return_value=repos)
        assert (
            await manager.distro_exists(repo_name)
            == bool(repo_name in repos))


@pytest.mark.asyncio
async def test_deb_repomanager_drop_distro(patches):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.aptly",
        ("DebRepoManager.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")

    with patched as (m_aptly, m_log):
        assert not await manager.drop_distro("DISTRO")

    assert (
        list(m_log.return_value.warning.call_args)
        == [("Removing existing repo DISTRO", ), {}])
    assert (
        list(m_aptly.call_args)
        == [("repo", "drop", "-force", "DISTRO"), {}])


@pytest.mark.asyncio
async def test_deb_repomanager_drop_published(patches):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.aptly",
        ("DebRepoManager.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")

    with patched as (m_aptly, m_log):
        assert not await manager.drop_published("DISTRO")

    assert (
        list(m_log.return_value.warning.call_args)
        == [("Removing existing published version DISTRO", ), {}])
    assert (
        list(m_aptly.call_args)
        == [("publish", "drop", "DISTRO"), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("exists", [True, False])
async def test_deb_repomanager_drop_snapshot(patches, exists):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.drop_published",
        "DebRepoManager.published_exists",
        "DebRepoManager.aptly",
        ("DebRepoManager.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")

    with patched as (m_rm, m_exists, m_aptly, m_log):
        m_exists.return_value = exists
        assert not await manager.drop_snapshot("DISTRO")

    assert (
        list(m_log.return_value.warning.call_args)
        == [("Removing existing snapshot DISTRO", ), {}])
    assert (
        list(m_exists.call_args)
        == [("DISTRO", ), {}])
    if exists:
        assert (
            list(m_rm.call_args)
            == [("DISTRO", ), {}])
    else:
        assert not m_rm.called
    assert (
        list(m_aptly.call_args)
        == [("snapshot", "drop", "-force",
             "DISTRO"), {}])


@pytest.mark.asyncio
async def test_deb_repomanager_include_changes(patches):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.include_changes_file",
        ("DebRepoManager.changes_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")
    files = [f"FILE{i}" for i in range(0, 5)]

    with patched as (m_inc, m_files):
        m_files.return_value = files
        assert not await manager.include_changes("DISTRO")


@pytest.mark.asyncio
@pytest.mark.parametrize("distro", ["DISTRO1", "DISTRO2"])
@pytest.mark.parametrize(
    "changes_file",
    ["foo.DISTRO1.changes",
     "bar.DISTRO2.changes",
     "baz.DISTRO3.changes",
     "DISTRO1.changes",
     "DISTRO2.changes",
     "foo.DISTRO1.notchanges",
     "bar.DISTRO2.notchanges"])
async def test_deb_repomanager_include_changes_file(
        patches, distro, changes_file):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.aptly",
        ("DebRepoManager.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")

    class DummyChangesFile:

        def __init__(self, name):
            self.name = name

        def __str__(self):
            return self.name

    dummy_file = DummyChangesFile(changes_file)

    with patched as (m_aptly, m_log):
        mock_strip = MagicMock()
        m_aptly.return_value.strip = mock_strip
        assert not await manager.include_changes_file(distro, dummy_file)

    if not changes_file.endswith(f".{distro}.changes"):
        assert not m_aptly.called
        assert not m_log.called
        return

    assert (
        list(m_aptly.call_args)
        == [("repo", "include", "-no-remove-files", changes_file), {}])
    assert (
        list(mock_strip.call_args)
        == [(), {}])
    mock_split = mock_strip.return_value.split
    assert (
        list(mock_split.call_args)
        == [("\n", ), {}])
    assert (
        list(mock_split.return_value.__getitem__.call_args)
        == [(-1, ), {}])
    assert (
        list(m_log.return_value.success.call_args)
        == [(mock_split.return_value.__getitem__.return_value, ), {}])


@pytest.mark.asyncio
async def test_deb_repomanager_publish(patches):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.publish_distro",
        ("DebRepoManager.aptly_root_dir",
         dict(new_callable=PropertyMock)),
        ("DebRepoManager.distros",
         dict(new_callable=PropertyMock)),
        ("DebRepoManager.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")
    distros = [f"DISTRO{i}" for i in range(0, 5)]

    with patched as (m_publish, m_dir, m_distros, m_log):
        m_distros.return_value = distros
        mock_dir = AsyncMock()
        m_dir.side_effect = mock_dir
        assert (
            await manager.publish()
            == mock_dir.return_value)

    assert (
        list(m_log.return_value.notice.call_args)
        == [("Building deb repository", ), {}])
    assert (
        list(list(c) for c in m_publish.call_args_list)
        == [[(distro, ), {}] for distro in distros])


@pytest.mark.asyncio
async def test_deb_repomanager_publish_distro(patches):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.create_distro",
        "DebRepoManager.include_changes",
        "DebRepoManager.create_snapshot",
        "DebRepoManager.publish_snapshot",
        prefix="envoy.distribution.repo.deb")
    order_mock = MagicMock()

    with patched as (m_create, m_inc, m_create_snap, m_publish_snap):
        m_create.side_effect = lambda x: order_mock("CREATE_DISTRO")
        m_inc.side_effect = lambda x: order_mock("INCLUDE")
        m_create_snap.side_effect = lambda x: order_mock("CREATE_SNAP")
        m_publish_snap.side_effect = lambda x: order_mock("PUBLISH_SNAP")
        assert not await manager.publish_distro("DISTRO")

    assert (
        list(list(c) for c in order_mock.call_args_list)
        == [[('CREATE_DISTRO',), {}],
            [('INCLUDE',), {}],
            [('CREATE_SNAP',), {}],
            [('PUBLISH_SNAP',), {}]])


@pytest.mark.asyncio
async def test_deb_repomanager_publish_snapshot(patches):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        "DebRepoManager.aptly",
        ("DebRepoManager.architectures",
         dict(new_callable=PropertyMock)),
        ("DebRepoManager.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")
    architectures = [f"ARCH{i}" for i in range(0, 5)]

    with patched as (m_aptly, m_arch, m_log):
        m_arch.return_value = architectures
        assert not await manager.publish_snapshot("DISTRO")

    assert (
        list(m_aptly.call_args)
        == [("publish", "snapshot",
             "-distribution=DISTRO",
             f"-architectures={','.join(architectures)}",
             "DISTRO"), {}])
    assert (
        list(m_log.return_value.info.call_args)
        == [(m_aptly.return_value, ), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "published_name",
    [f"PUBLISHED{i}" for i in range(0, 5)])
async def test_deb_repomanager_published_exists(patches, published_name):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        ("DebRepoManager.aptly_published",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")
    published = [f"PUBLISHED{i}" for i in range(1, 3)]

    with patched as (m_published, ):
        m_published.side_effect = AsyncMock(return_value=published)
        assert (
            await manager.published_exists(published_name)
            == bool(published_name in published))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "snapshot_name",
    [f"SNAPSHOT{i}" for i in range(0, 5)])
async def test_deb_repomanager_snapshot_exists(patches, snapshot_name):
    manager = repo.DebRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    patched = patches(
        ("DebRepoManager.aptly_snapshots",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.deb")
    snapshots = [f"SNAPSHOT{i}" for i in range(1, 3)]

    with patched as (m_snapshots, ):
        m_snapshots.side_effect = AsyncMock(return_value=snapshots)
        assert (
            await manager.snapshot_exists(snapshot_name)
            == bool(snapshot_name in snapshots))
