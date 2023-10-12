
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.run.runner import Runner

from envoy.base import utils


# BaseProjectRunner

def test_baseprojectrunner_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "runner.Runner.__init__",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_super, ):
        m_super.return_value = None
        runner = utils.project_runner.BaseProjectRunner(*args, **kwargs)

    assert isinstance(runner, Runner)
    assert (
        m_super.call_args
        == [args, kwargs])


@pytest.mark.parametrize("token", [None, "TOKEN"])
def test_baseprojectrunner_github_token(patches, token):
    runner = utils.project_runner.BaseProjectRunner()
    patched = patches(
        "os",
        "pathlib",
        "ENV_GITHUB_TOKEN",
        ("BaseProjectRunner.args",
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


def test_baseprojectrunner_path(patches):
    runner = utils.project_runner.BaseProjectRunner()
    patched = patches(
        "pathlib",
        ("BaseProjectRunner.args",
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


def test_baseprojectrunner_project(patches):
    runner = utils.project_runner.BaseProjectRunner()
    patched = patches(
        "utils",
        ("BaseProjectRunner.github_token",
         dict(new_callable=PropertyMock)),
        ("BaseProjectRunner.path",
         dict(new_callable=PropertyMock)),
        ("BaseProjectRunner.repo_name",
         dict(new_callable=PropertyMock)),
        ("BaseProjectRunner.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_utils, m_token, m_path, m_repo, m_session):
        assert (
            runner.project
            == m_utils.Project.return_value)

    assert (
        m_utils.Project.call_args
        == [(),
            dict(path=m_path.return_value,
                 session=m_session.return_value,
                 repo=m_repo.return_value,
                 github_token=m_token.return_value)])
    assert "project" in runner.__dict__


def test_baseprojectrunner_repo_name(patches):
    runner = utils.project_runner.BaseProjectRunner()
    patched = patches(
        ("BaseProjectRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_args, ):
        assert (
            runner.repo_name
            == m_args.return_value.repo)

    assert "repo_name" not in runner.__dict__


def test_baseprojectrunner_session(patches):
    runner = utils.project_runner.BaseProjectRunner()
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


# ProjectRunner

def test_projectrunner_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "BaseProjectRunner.__init__",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_super, ):
        m_super.return_value = None
        runner = utils.ProjectRunner(*args, **kwargs)

    assert isinstance(runner, utils.project_runner.BaseProjectRunner)
    assert (
        m_super.call_args
        == [args, kwargs])


@pytest.mark.parametrize("prop", ["command", "nosync", "patch"])
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


@pytest.mark.parametrize("command", [None, "COMMAND", "publish"])
@pytest.mark.parametrize("nocommit", [True, False])
def test_projectrunner_nocommit(patches, command, nocommit):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_args, ):
        m_args.return_value.command = command
        m_args.return_value.nocommit = nocommit
        assert (
            runner.nocommit
            == (command == "publish" or nocommit))

    assert "nocommit" not in runner.__dict__


def test_projectrunner_add_arguments(patches):
    runner = utils.ProjectRunner()
    parser = MagicMock()
    patched = patches(
        "BaseProjectRunner.add_arguments",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_super, ):
        runner.add_arguments(parser)

    assert (
        m_super.call_args
        == [(parser, ), {}])
    assert (
        parser.add_argument.call_args_list
        == [[('command',),
             {'choices': ['sync', 'release', 'dev', 'publish', 'trigger']}],
            [('path',),
             {'default': '.'}],
            [('--app-key',),
             {'default': 'GITHUB_APP_KEY'}],
            [('--app-keyfile',),
             {'default': ''}],
            [('--github_token',), {}],
            [('--nosync',),
             {'action': 'store_true'}],
            [('--nocommit',),
             {'action': 'store_true'}],
            [('--patch',),
             {'action': 'store_true'}],
            [('--repo',),
             {'default': ''}],
            [('--dry-run',),
             {'action': 'store_true'}],
            [('--release-message-path',),
             {'default': ''}],
            [('--publish-assets',),
             {'default': ''}],
            [('--publish-commitish',),
             {'default': ''}],
            [('--publish-commit-message',),
             {'action': 'store_true'}],
            [('--publish-dev',),
             {'action': 'store_true'}],
            [('--publish-latest',),
             {'action': 'store_true'}],
            [('--publish-generate-notes',),
             {'action': 'store_true'}],
            [('--trigger-ref',),
             {'default': ''}],
            [('--trigger-app-id',),
             {'default': ''}],
            [('--trigger-installation-id',),
             {'default': ''}],
            [('--trigger-workflow',),
             {'default': ''}],
            [('--trigger-inputs',),
             {'default': ''}]])


async def test_projectrunner_commit(iters, patches):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.project",
         dict(new_callable=PropertyMock)),
        "ProjectRunner.msg_for_commit",
        prefix="envoy.base.utils.project_runner")
    change = MagicMock()
    paths = iters()

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


@pytest.mark.parametrize(
    "action", ["dev", "release", "sync", "publish", "trigger"])
@pytest.mark.parametrize("nosync", [True, False])
async def test_projectrunner_handle_action(patches, action, nosync):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.args",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.command",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.nosync",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.release_message",
         dict(new_callable=PropertyMock)),
        "ProjectRunner.run_dev",
        "ProjectRunner.run_publish",
        "ProjectRunner.run_release",
        "ProjectRunner.run_sync",
        "ProjectRunner.run_trigger",
        prefix="envoy.base.utils.project_runner")

    with patched as patchy:
        (m_args, m_command, m_nosync, m_msg,
         m_dev, m_publish, m_release, m_sync,
         m_trigger) = patchy
        m_command.return_value = action
        m_nosync.return_value = nosync
        result = await runner.handle_action()

    if action == "publish":
        assert (
            m_publish.call_args
            == [(),
                dict(dry_run=m_args.return_value.dry_run,
                     assets=m_args.return_value.publish_assets,
                     commitish=m_args.return_value.publish_commitish,
                     dev=m_args.return_value.publish_dev,
                     publish_commit_message=(
                         m_args.return_value.publish_commit_message),
                     latest=m_args.return_value.publish_latest)])
        assert result == dict(publish=m_publish.return_value)
        assert not m_sync.called
        return
    if action == "dev":
        assert (
            m_dev.call_args
            == [(), {}])
        assert result["dev"] == m_dev.return_value
        assert "release" not in result
    if action == "release":
        assert (
            m_release.call_args
            == [(), dict(release_message=m_msg.return_value)])
        assert result["release"] == m_release.return_value
        assert "dev" not in result
    if action == "trigger":
        assert (
            m_trigger.call_args
            == [(), {}])
        assert result["trigger"] == m_trigger.return_value
    if nosync or action == "trigger":
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
        "_version",
        "COMMIT_MSGS",
        "utils",
        "ProjectRunner._previous_version",
        ("ProjectRunner.command",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")
    change = MagicMock()

    with patched as (m_version, m_msgs, m_utils, m_previous, m_command):
        assert (
            runner.msg_for_commit(change)
            == m_msgs.__getitem__.return_value.format.return_value)

    assert (
        m_msgs.__getitem__.call_args
        == [(m_command.return_value, ), {}])
    assert (
        m_msgs.__getitem__.return_value.format.call_args
        == [(),
            dict(change=change,
                 version_string=f"v{m_version.Version.return_value}",
                 minor_version=f"v{m_utils.minor_version_for.return_value}",
                 previous_release_version=f"v{m_previous.return_value}",
                 envoy_docker_image=utils.project_runner.ENVOY_DOCKER_IMAGE,
                 envoy_docs=utils.project_runner.ENVOY_DOCS,
                 envoy_repo=utils.project_runner.ENVOY_REPO)])

    assert (
        m_utils.minor_version_for.call_args
        == [(m_version.Version.return_value, ), {}])
    assert (
        m_version.Version.call_args
        == [(change.__getitem__.return_value.__getitem__.return_value, ), {}])
    assert (
        change.__getitem__.call_args
        == [("release", ), {}])
    assert (
        change.__getitem__.return_value.__getitem__.call_args
        == [("version", ), {}])


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


@pytest.mark.parametrize("nochange", [True, False])
@pytest.mark.parametrize("dry_run", [True, False])
async def test_projectrunner_publish(patches, nochange, dry_run):
    runner = utils.ProjectRunner()
    patched = patches(
        "utils",
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")
    kwargs = dict(dry_run=dry_run)
    changemock = MagicMock()
    assetmocks = []

    async def publish(**kwargs):
        if nochange:
            return
        yield changemock
        for i in range(0, 5):
            assetmock = MagicMock()
            assetmock.__contains__.return_value = i % 2
            assetmocks.append(assetmock)
            yield assetmock

    with patched as (m_utils, m_log, m_project, ):
        m_project.return_value.publish.side_effect = publish
        if nochange:
            with pytest.raises(utils.exceptions.PublishError) as e:
                await runner.run_publish(**kwargs)
        else:
            assert (
                await runner.run_publish(**kwargs)
                == m_utils.typed.return_value)

    assert (
        m_project.return_value.publish.call_args
        == [(), kwargs])
    if nochange:
        assert e.value.args[0] == "Unknown publishing error"
        assert not m_utils.typed.called
        assert not m_log.called
        return
    assert (
        m_utils.typed.call_args
        == [(utils.typing.ProjectPublishResultDict, changemock), {}])
    dry_run = (
        " (dry run)"
        if dry_run
        else "")
    release_msg = (
        f"[release] Release ({changemock.__getitem__.return_value}) "
        f"created{dry_run} from branch/commit: "
        f"{changemock.__getitem__.return_value}")
    assert (
        m_log.return_value.success.call_args_list[0]
        == [(release_msg, ), {}])
    assert (
        changemock.__getitem__.call_args_list
        == [[(k, ), {}]
            for k
            in ("tag_name", "commitish")])
    assert (
        m_log.return_value.error.call_args_list
        == [[((
            f"[release] Something went wrong uploading{dry_run}: "
            f"{result.__getitem__.return_value} -> "
            f"{result.__getitem__.return_value}\n"
            f"{result.__getitem__.return_value}"), ), {}]
            for i, result in enumerate(assetmocks)
            if i % 2])
    assert (
        m_log.return_value.success.call_args_list[1:]
        == [[((
            f"[release] Artefact uploaded{dry_run}: "
            f"{result.__getitem__.return_value} -> "
            f"{result.__getitem__.return_value}"), ), {}]
            for i, result in enumerate(assetmocks)
            if not i % 2])
    for i, mock in enumerate(assetmocks):
        assert (
            mock.__contains__.call_args
            == [("error", ), {}])
        ks = (
            ("name", "url")
            if not i % 2
            else ("name", "url", "error"))
        assert (
            mock.__getitem__.call_args_list
            == [[(k, ), {}]
                for k
                in ks])


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


@pytest.mark.parametrize("release_message", [None, "", "MESSAGE"])
async def test_projectrunner_run_release(patches, release_message):
    runner = utils.ProjectRunner()
    message_mock = MagicMock()
    message_mock.__bool__.return_value = bool(release_message)
    kwargs = (
        dict(release_message=message_mock)
        if release_message is not None
        else {})
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
            await runner.run_release(**kwargs)
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
    assert (
        release.return_value.__setitem__.call_args
        == [("message",
             f"{message_mock.strip.return_value}\n"
             if release_message
             else "", ),
            {}])
    assert (
        message_mock.strip.call_args
        == ([(), {}]
            if release_message
            else None))


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


@pytest.mark.parametrize("keyfile", [True, False])
@pytest.mark.parametrize("inputs", [True, False])
async def test_projectrunner_run_trigger(patches, keyfile, inputs):
    runner = utils.ProjectRunner()
    patched = patches(
        "dict",
        "json",
        "os",
        "pathlib",
        ("ProjectRunner.args",
         dict(new_callable=PropertyMock)),
        ("ProjectRunner.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_dict, m_json, m_os, m_plib, m_args, m_project):
        m_args.return_value.app_keyfile = keyfile
        m_args.return_value.trigger_inputs = inputs
        trigger = AsyncMock()
        m_project.return_value.trigger = trigger
        assert (
            await runner.run_trigger()
            == trigger.return_value)

    if keyfile:
        assert not m_os.environ.__getitem__.called
        assert (
            m_plib.Path.call_args
            == [(m_args.return_value.app_keyfile, ), {}])
        assert (
            m_plib.Path.return_value.read_bytes.call_args
            == [(), {}])
        key = m_plib.Path.return_value.read_bytes.return_value
    else:
        assert (
            m_os.environ.__getitem__.call_args
            == [(m_args.return_value.app_key, ), {}])
        assert (
            m_os.environ.__getitem__.return_value.encode.call_args
            == [("utf-8", ), {}])
        key = m_os.environ.__getitem__.return_value.encode.return_value
    if inputs:
        assert (
            m_json.loads.call_args
            == [(inputs, ), {}])
        expected_inputs = m_json.loads.return_value
    else:
        assert not m_json.loads.called
        expected_inputs = {}
    assert (
        m_dict.call_args
        == [(),
            dict(ref=m_args.return_value.trigger_ref,
                 inputs=expected_inputs)])
    assert (
        trigger.call_args
        == [(),
            dict(workflow=m_args.return_value.trigger_workflow,
                 app_id=m_args.return_value.trigger_app_id,
                 installation_id=m_args.return_value.trigger_installation_id,
                 key=key,
                 data=m_dict.return_value)])


@pytest.mark.parametrize("change", [True, False])
def test_projectrunner__log_changelog(iters, patches, change):
    runner = utils.ProjectRunner()
    patched = patches(
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")
    changes = iters(dict)
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
def test_projectrunner__log_inventory(iters, patches, change):
    runner = utils.ProjectRunner()
    patched = patches(
        "utils",
        ("ProjectRunner.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")
    changes = iters(dict, cb=lambda i: (f"K{i}", (i % 2)), count=10)
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


@pytest.mark.parametrize("micro", range(0, 5))
def test_projectrunner__previous_version(patches, micro):
    runner = utils.ProjectRunner()
    patched = patches(
        "_version",
        prefix="envoy.base.utils.project_runner")
    version = MagicMock()
    version.micro = micro

    with patched as (m_version, ):
        assert (
            runner._previous_version(version)
            == m_version.Version.return_value)
    expected_micro = (
        micro - (1 if micro != 0 else 0))
    assert (
        m_version.Version.call_args
        == [(f"{version.major}."
             f"{version.minor.__sub__.return_value}."
             f"{expected_micro}", ), {}])
    assert (
        version.minor.__sub__.call_args
        == [(1 if micro == 0 else 0, ), {}])


def test_projectdatarunner_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "BaseProjectRunner.__init__",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_super, ):
        m_super.return_value = None
        runner = utils.ProjectDataRunner(*args, **kwargs)

    assert isinstance(runner, utils.project_runner.BaseProjectRunner)
    assert (
        m_super.call_args
        == [args, kwargs])


def test_projecdatatrunner_add_arguments(patches):
    runner = utils.ProjectDataRunner()
    parser = MagicMock()
    patched = patches(
        "BaseProjectRunner.add_arguments",
        prefix="envoy.base.utils.project_runner")

    with patched as (m_super, ):
        runner.add_arguments(parser)

    assert (
        m_super.call_args
        == [(parser, ), {}])
    assert (
        parser.add_argument.call_args_list
        == [[('path',),
             {'default': '.'}],
            [('--repo',),
             {'default': ''}],
            [('--github_token',), {}]])


async def test_projectdatarunner_run(patches):
    runner = utils.ProjectDataRunner()
    patched = patches(
        "print",
        ("ProjectDataRunner.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.project_runner")

    with patched as (m_print, m_project):
        json_data = AsyncMock()
        m_project.return_value.json_data = json_data()
        assert not await runner.run()

    assert (
        m_print.call_args
        == [(json_data.return_value, ), {}])
