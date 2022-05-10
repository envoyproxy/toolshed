
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.run.runner import Runner

from envoy.base import utils


def test_projectrunner_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "runner.Runner.__init__",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_super, ):
        m_super.return_value = None
        runner = utils.ProjectRunner(*args, **kwargs)

    assert isinstance(runner, Runner)
    assert (
        m_super.call_args
        == [args, kwargs])


@pytest.mark.parametrize("prop", ["command", "nocommit", "nosync", "patch"])
def test_projectrunner_arg_props(patches, prop):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_args, ):
        assert (
            getattr(runner, prop)
            == getattr(m_args.return_value, prop))

    assert prop not in runner.__dict__


@pytest.mark.parametrize("token", [None, "TOKEN"])
def test_projectrunner_github_token(patches, token):
    runner = utils.ProjectRunner()
    patched = patches(
        "os",
        "pathlib",
        "ENV_GITHUB_TOKEN",
        ("ProjectRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_os, m_plib, m_env, m_args):
        m_args.return_value.github_token = token
        assert (
            runner.github_token
            == ((m_plib.Path.return_value.read_text
                            .return_value.strip
                            .return_value)
                if token
                else m_os.getenv.return_value))

    assert "github_token" not in runner.__dict__
    if not token:
        assert not m_plib.Path.called
        assert (
            m_os.getenv.call_args
            == [(m_env, ), {}])
        return
    assert not m_os.getenv.called
    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.github_token, ), {}])
    assert (
        m_plib.Path.return_value.read_text.call_args
        == [(), {}])
    assert (
        m_plib.Path.return_value.read_text.return_value.strip.call_args
        == [(), {}])


def test_projectrunner_path(patches):
    runner = utils.ProjectRunner()
    patched = patches(
        "pathlib",
        ("ProjectRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_plib, m_args):
        assert (
            runner.path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.path, ), {}])
    assert "path" in runner.__dict__


def test_projectrunner_project(patches):
    runner = utils.ProjectRunner()
    patched = patches(
        "utils",
        ("ProjectRunner.github_token",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.path",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_utils, m_token, m_path, m_session):
        assert (
            runner.project
            == m_utils.Project.return_value)

    assert (
        m_utils.Project.call_args
        == [(),
            dict(path=m_path.return_value,
                 session=m_session.return_value,
                 github_token=m_token.return_value)])
    assert "project" in runner.__dict__


def test_projectrunner_session(patches):
    runner = utils.ProjectRunner()
    patched = patches(
        "aiohttp",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_aiohttp, ):
        assert (
            runner.session
            == m_aiohttp.ClientSession.return_value)

    assert (
        m_aiohttp.ClientSession.call_args
        == [(), {}])
    assert "session" in runner.__dict__


def test_projecrunner_add_arguments(patches):
    runner = utils.ProjectRunner()
    parser = MagicMock()
    patched = patches(
        "runner.Runner.add_arguments",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_super, ):
        runner.add_arguments(parser)

    assert (
        m_super.call_args
        == [(parser, ), {}])
    assert (
        parser.add_argument.call_args_list
        == [[('command',),
             {'choices': ['sync', 'release', 'dev']}],
            [('path',),
             {'default': '.'}],
            [('--github_token',), {}],
            [('--nosync',),
             {'action': 'store_true'}],
            [('--nocommit',),
             {'action': 'store_true'}],
            [('--patch',),
             {'action': 'store_true'}]])


async def test_projectrunner_commit(patches):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.project",
         dict(new_callable=PropertyMock)),
        "ProjectRunner.msg_for_commit",
        prefix="envoy.base.utils.project_runner")
    change = MagicMock()
    paths = [f"P{i}" for i in range(0, 5)]

    async def committer(c, m):
        for p in paths:
            yield p

    with patched as (m_log, m_proj, m_msg):
        m_proj.return_value.commit.side_effect = committer
        assert not await runner.commit(change)

    assert (
        m_proj.return_value.commit.call_args
        == [(change, m_msg.return_value), {}])
    assert (
        m_log.return_value.info.call_args_list
        == ([[(f"[git] add: {p}", ), {}]
             for p in paths]
            + [[(f"[git] commit: \"{m_msg.return_value}\"", ),
                {}]]))
    assert (
        m_msg.call_args
        == [(change, ), {}])


@pytest.mark.parametrize("action", ["dev", "release", "sync"])
@pytest.mark.parametrize("nosync", [True, False])
async def test_projectrunner_handle_action(patches, action, nosync):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.command",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.nosync",
         dict(new_callable=PropertyMock)),
        "ProjectRunner.run_dev",
        "ProjectRunner.run_release",
        "ProjectRunner.run_sync",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_command, m_nosync, m_dev, m_release, m_sync):
        m_command.return_value = action
        m_nosync.return_value = nosync
        result = await runner.handle_action()

    if action == "dev":
        assert (
            m_dev.call_args
            == [(), {}])
        assert result["dev"] == m_dev.return_value
        assert "release" not in result
    if action == "release":
        assert (
            m_release.call_args
            == [(), {}])
        assert result["release"] == m_release.return_value
        assert "dev" not in result
    if nosync:
        assert "sync" not in result
        assert not m_sync.called
        return
    assert (
        m_sync.call_args
        == [(), {}])
    assert result["sync"] == m_sync.return_value


def test_projectrunner_msg_for_commit(patches):
    runner = utils.ProjectRunner()
    patched = patches(
        "COMMIT_MSGS",
        ("ProjectRunner.command",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")
    change = MagicMock()

    with patched as (m_msgs, m_command):
        assert (
            runner.msg_for_commit(change)
            == m_msgs.__getitem__.return_value.format.return_value)

    assert (
        m_msgs.__getitem__.call_args
        == [(m_command.return_value, ), {}])
    assert (
        m_msgs.__getitem__.return_value.format.call_args
        == [(), dict(change=change)])


def test_projectrunner_notify_complete(patches):
    runner = utils.ProjectRunner()
    patched = patches(
        "NOTIFY_MSGS",
        ("ProjectRunner.command",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")
    change = MagicMock()

    with patched as (m_msgs, m_command, m_log):
        assert not runner.notify_complete(change)

    assert (
        m_log.return_value.notice.call_args
        == [(m_msgs.__getitem__.return_value.format.return_value, ),
            {}])
    assert (
        m_msgs.__getitem__.call_args
        == [(m_command.return_value, ), {}])
    assert (
        m_msgs.__getitem__.return_value.format.call_args
        == [(), dict(change=change)])


@pytest.mark.parametrize("nocommit", [True, False])
async def test_projectrunner_run(patches, nocommit):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.nocommit",
         dict(new_callable=PropertyMock)),
        "ProjectRunner.commit",
        "ProjectRunner.handle_action",
        "ProjectRunner.notify_complete",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_nocommit, m_commit, m_handle, m_notify):
        m_nocommit.return_value = nocommit
        assert not await runner.run()

    assert (
        m_handle.call_args
        == [(), {}])
    if nocommit:
        assert not m_commit.called
    else:
        assert (
            m_commit.call_args
            == [(m_handle.return_value, ), {}])
    assert (
        m_notify.call_args
        == [(m_handle.return_value, ), {}])


async def test_projectrunner_run_dev(patches):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.patch",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_log, m_patch, m_project):
        dev = AsyncMock()
        m_project.return_value.dev = dev
        assert (
            await runner.run_dev()
            == dev.return_value)

    assert (
        dev.call_args
        == [(), dict(patch=m_patch.return_value)])
    assert (
        m_log.return_value.success.call_args_list
        == [[(f"[version] {dev.return_value.__getitem__.return_value}", ),
             {}],
            [(("[changelog] add: "
               f"{dev.return_value.__getitem__.return_value}"), ),
             {}]])
    assert (
        dev.return_value.__getitem__.call_args_list
        == [[("version", ), {}],
            [("old_version", ), {}]])


async def test_projectrunner_run_release(patches):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_log, m_project):
        release = AsyncMock()
        m_project.return_value.release = release
        assert (
            await runner.run_release()
            == release.return_value)

    assert (
        release.call_args
        == [(), {}])
    assert (
        m_log.return_value.success.call_args_list
        == [[(f"[version] {release.return_value.__getitem__.return_value}", ),
             {}],
            [(("[changelog] current: "
               f"{release.return_value.__getitem__.return_value}"), ),
             {}]])
    assert (
        release.return_value.__getitem__.call_args_list
        == [[("version", ), {}],
            [("date", ), {}]])


async def test_projectrunner_run_sync(patches):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.project",
         dict(new_callable=PropertyMock)),
        "ProjectRunner._log_changelog",
        "ProjectRunner._log_inventory",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_project, m_clog, m_inv):
        sync = AsyncMock()
        m_project.return_value.sync = sync
        assert (
            await runner.run_sync()
            == sync.return_value)

    assert (
        sync.call_args
        == [(), {}])
    assert (
        m_clog.call_args
        == [(sync.return_value.__getitem__.return_value, ),
            {}])
    assert (
        m_inv.call_args
        == [(sync.return_value.__getitem__.return_value, ),
            {}])
    assert (
        sync.return_value.__getitem__.call_args_list
        == [[("changelog", ), {}],
            [("inventory", ), {}]])


@pytest.mark.parametrize("change", [True, False])
def test_projectrunner__log_changelog(patches, change):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")
    changes = {f"K{i}": f"v{i}" for i in range(0, 5)}
    if not change:
        change = {}
    else:
        change = MagicMock()
        change.items.return_value = changes.items()

    with patched as (m_log, ):
        assert not runner._log_changelog(change)

    if not change:
        assert (
            m_log.return_value.success.call_args_list
            == [[("[changelog] up to date", ), {}]])
    else:
        assert (
            m_log.return_value.success.call_args_list
            == [[(f"[changelog] add: {version}", ), {}]
                for version in changes])


@pytest.mark.parametrize("change", [True, False])
def test_projectrunner__log_inventory(patches, change):
    runner = utils.ProjectRunner()
    patched = patches(
        "utils",
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")
    changes = {f"K{i}": (i % 2) for i in range(0, 10)}
    if not change:
        change = {}
    else:
        change = MagicMock()
        change.items.return_value = changes.items()

    with patched as (m_utils, m_log):
        assert not runner._log_inventory(change)

    if not change:
        assert (
            m_log.return_value.success.call_args_list
            == [[("[inventory] up to date", ), {}]])
        return
    assert (
        m_log.return_value.success.call_args_list
        == [[(("[inventory] update: "
               f"{m_utils.minor_version_for.return_value} -> "
               f"{version}"), ), {}]
            for version, sync
            in changes.items()
            if sync])
    assert (
        m_log.return_value.warning.call_args_list
        == [[(("[inventory] newer version available "
               f"({version}), but no inventory found"), ), {}]
            for version, sync
            in changes.items()
            if not sync])
    assert (
        m_utils.minor_version_for.call_args_list
        == [[(v, ), {}]
            for v, sync
            in changes.items()
            if sync])
